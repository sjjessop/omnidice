
import setuptools

setuptools.setup(
    name='omnidice',
    version='0.0.1',
    python_requires='>=3.7.3',
    packages=setuptools.find_packages(),
    install_requires=[
        'coverage',
        'flake8',
        'pytest',
    ],
    extras_require={
        'pd': ['pandas'],
    }
)
