
import setuptools

setuptools.setup(
    name='omnidice',
    version='1.2.0',
    python_requires='>=3.6.8',
    packages=setuptools.find_packages(),
    install_requires=[
        'dataclasses;python_version<"3.7"',
        'pytest',
    ],
    extras_require={
        'dev': [
            # https://github.com/pytest-dev/pytest/issues/7632
            'coverage>=5.2.1',
            'flake8',
            'mypy>=0.782',
            'pytest-cov',
            'Pygments>=2.6.1',
            'sphinx>=3.1.2,<3.3',
            'wheel',
        ],
        'pd': ['pandas'],
    },
    package_data={
        'omnidice': ['py.typed'],
    },
)
