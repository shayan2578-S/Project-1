"""Execute every notebook cell using the project environment, retaining outputs."""
from pathlib import Path
import os
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

ROOT = Path(__file__).resolve().parents[1]
cache = ROOT / '.cache'
cache.mkdir(exist_ok=True)
os.environ['IPYTHONDIR'] = str(cache / 'ipython')
os.environ['JUPYTER_RUNTIME_DIR'] = str(cache / 'jupyter')
os.environ['XDG_CACHE_HOME'] = str(cache)
os.environ['MPLCONFIGDIR'] = str(cache / 'matplotlib')
path = ROOT / 'notebooks/01_access_to_opportunity.ipynb'
notebook = nbformat.read(path, as_version=4)
manager = KernelManager(kernel_name='opportunity', kernel_spec_manager=KernelSpecManager(
    kernel_dirs=[str(ROOT / '.venv/share/jupyter/kernels')]))
client = NotebookClient(notebook, km=manager, timeout=180,
                        resources={'metadata': {'path': str(ROOT)}}, allow_errors=False)
client.execute()
nbformat.write(notebook, path)
print(f'Executed {sum(cell.cell_type == "code" for cell in notebook.cells)} code cells without errors.')
