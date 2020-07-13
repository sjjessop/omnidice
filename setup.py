
import setuptools

setuptools.setup(
    name='omnidice',
    version='0.0.1',
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
            'sphinx>=3.1.2',
        ],
        'pd': ['pandas'],
    }
)
