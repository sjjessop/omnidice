
import setuptools

setuptools.setup(
    name='omnidice',
    version='1.2.2',
    python_requires='>=3.7.0',
    packages=setuptools.find_packages(),
    install_requires=[
        'pytest',
    ],
    extras_require={
        'dev': [
            # https://github.com/pytest-dev/pytest/issues/7632
            'coverage>=5.2.1',
            'flake8',
            'isort',
            'mypy==1.4.1',
            'pytest-cov',
            'Pygments>=2.6.1',
            'sphinx>=3.3.0',
            'wheel',
        ],
        'dev:python_version<"3.8"': [
            # https://github.com/python/importlib_metadata/issues/406
            'importlib-metadata<5'
        ],
        'pd': ['pandas'],
    },
    package_data={
        'omnidice': ['py.typed'],
    },
)
