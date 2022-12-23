from setuptools import setup

packages = ['AiBot']

package_data = {
}

install_requires = [
    "loguru~=0.6.0"
]

setup_kwargs = {
    'name': 'AiBot.py',
    'version': '1.0.4',
    'description': '...',
    'long_description': '...',
    'long_description_content_type': 'text/markdown',
    'author': 'waitan2018',
    'author_email': None,
    'maintainer': 'waitan2018',
    'maintainer_email': None,
    'url': 'https://github.com/waitan2018/AiBot',
    'packages': packages,
    'package_data': package_data,
    'install_requires': install_requires,
    'python_requires': '>=3.6,<4.0',
}

setup(**setup_kwargs)
