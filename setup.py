
import setuptools

setuptools.setup(
    name='omnidice',
    version='1.0.0',
    python_requires='>=3.7.3',
    packages=setuptools.find_packages(),
    install_requires=[
        'pytest',
    ],
    extras_require={
        'dev': [
            'coverage',
            'flake8',
            'm2r',
            'mypy>=0.782',
            'pytest-cov',
            'Pygments>=2.6.1',
            'sphinx>=3.1.2',
            'wheel',
        ],
        'pd': ['pandas'],
    },
    package_data={
        'omnidice': ['py.typed'],
    },
)
