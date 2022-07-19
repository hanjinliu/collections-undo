from setuptools import setup, find_packages

with open("undo/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]

with open("README.md") as f:
    readme = f.read()

setup(
    name="undo",
    version=VERSION,
    description="General undo/redo framework for Python",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="MIT",
    download_url="https://github.com/hanjinliu/undo",
    packages=find_packages(exclude=["docs", "examples", "rst", "tests", "tests.*"]),
    package_data={"undo": ["**/*.pyi", "*.pyi"]},
    install_requires=[
        "typing_extensions",
        "frozenlist",
    ],
    python_requires=">=3.8",
)
