import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="crow-security-ng",
    version="0.1.5",
    author="Tubalainen",
    author_email="tubalainen@gmail.com",
    description="Python library for Crow Security Alarm Systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tubalainen/crow_security_ng",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "aiohttp",
    ],
    python_requires='>=3.7',
)