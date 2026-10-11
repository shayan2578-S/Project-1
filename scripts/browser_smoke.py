"""Browser check against a running Streamlit app; no mocked or substitute data."""
from pathlib import Path
import argparse
import csv
from datetime import datetime, timezone
import json
import shutil

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8501')
parser.add_argument('--chromium', default=shutil.which('chromium'))
args = parser.parse_args()
artifacts = ROOT / 'artifacts'
artifacts.mkdir(exist_ok=True)
quality = json.loads((ROOT / 'reports/data_quality.json').read_text())
expected_total = quality['rows']
expected_wakefield = quality['district_counts']['E08000036']

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=args.chromium, headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1450}, device_scale_factor=1)
    errors, failed_requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('requestfailed', lambda request: failed_requests.append({'url': request.url, 'failure': request.failure}))
    page.goto(args.url, wait_until='networkidle')
    page.get_by_text('A closer look', exact=True).wait_for(timeout=60000)
    expect(page.get_by_test_id('stMetricValue').first).to_have_text(f'{expected_total:,}')

    def wait_for_map(count):
        page.wait_for_function('''count => {
            const plot = document.querySelector('.js-plotly-plot');
            const map = plot?._fullLayout?.map?._subplot?.map;
            return plot?.data?.[1]?.locations?.length === count && map?.loaded();
        }''', arg=count, timeout=60000)

    wait_for_map(expected_total)
    assert page.locator('.maplibregl-canvas').count() == 1
    page.screenshot(path=str(ROOT / 'docs/images/dashboard.png'), full_page=True)

    # Remove two tags through the actual interface and wait for the real rerun.
    selector = page.get_by_test_id('stMultiSelect')
    for district in ['Leeds', 'Bradford']:
        selector.locator(f'[data-baseweb="tag"][aria-label="{district}, close by backspace"] svg').click()
    expect(page.get_by_test_id('stMetricValue').first).to_have_text(f'{expected_wakefield:,}', timeout=60000)
    wait_for_map(expected_wakefield)

    indicator = page.get_by_test_id('stSelectbox').filter(has_text='Map indicator')
    indicator.get_by_role('combobox').click()
    page.get_by_role('option', name='Income deprivation (%)', exact=True).click()
    page.wait_for_function('''() => {
        const trace = document.querySelector('.js-plotly-plot')?.data?.[1];
        return trace?.hovertemplate?.includes('Income deprivation (%):');
    }''', timeout=60000)
    wait_for_map(expected_wakefield)

    page.get_by_role('tab', name='Compare districts', exact=True).click()
    expect(page.get_by_text('Keep weighting visible', exact=True)).to_be_visible()
    page.get_by_role('tab', name='Priority & sensitivity', exact=True).click()
    expect(page.get_by_text('A review list, with the ingredients visible', exact=True)).to_be_visible()
    # Streamlit styles the native input as hidden; users activate its label.
    page.get_by_test_id('stCheckbox').get_by_text('Show only areas in all three adverse tails', exact=True).click()
    expect(page.get_by_role('checkbox', name='Show only areas in all three adverse tails')).to_be_checked()
    page.wait_for_timeout(1500)
    with page.expect_download() as downloaded:
        page.get_by_role('button', name='Download displayed review list').click()
    download_path = artifacts / 'browser_review_list.csv'
    downloaded.value.save_as(download_path)
    with download_path.open() as file:
        review_rows = list(csv.DictReader(file))
    assert review_rows and {row['district_name'] for row in review_rows} == {'Wakefield'}
    assert all(row['triple_priority'] == 'True' for row in review_rows)
    assert {row['lsoa_code'] for row in review_rows} == {'E01011792', 'E01011811'}

    page.get_by_role('tab', name='Methods & sources', exact=True).click()
    expect(page.get_by_text('What this study can—and cannot—say', exact=True)).to_be_visible()
    assert page.get_by_test_id('stException').count() == 0
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'status': 'passed' if not errors and not failed_requests else 'failed',
              'browser': browser.version, 'initial_map_areas': expected_total,
              'filtered_map_areas': expected_wakefield, 'downloaded_flagged_rows': len(review_rows),
              'indicator_switch': 'passed', 'tabs': 'passed', 'page_errors': errors, 'failed_requests': failed_requests}
    (artifacts / 'browser_smoke.json').write_text(json.dumps(report, indent=2) + '\n')
    browser.close()
    assert not errors and not failed_requests, report
    print(json.dumps(report, indent=2))
