import sys

sys.stderr.write(
    """
    =======================================================================
    collections-undo does not support `python setup.py install`. Please use

        $ python -m pip install .

    instead.
    =======================================================================
    """
)
sys.exit(1)

setup(
    name="collections-undo",
    description="General undo/redo framework for Python",
    long_description_content_type="text/markdown",
    author="Hanjin Liu",
    author_email="liuhanjin-sc@g.ecc.u-tokyo.ac.jp",
    license="MIT",
    download_url="https://github.com/hanjinliu/collections-undo",
    install_requires=[
        "typing_extensions",
    ],
    python_requires=">=3.8",
)
