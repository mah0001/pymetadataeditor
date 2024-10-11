# pyMetadataEditor

Go to demo.ipynb to see examples of how to use this tool.

This is a work in progress python implementation of the r package metadataeditr (https://github.com/ihsn/metadataeditr).


## Setting up the python environment

This library uses Poetry for dependency management (https://python-poetry.org/docs/basic-usage/).

In your python environment run `pip install poetry` then navigate to the pymetadataeditor folder and run `poetry install` or, if that doesn't work, try `python -m poetry install`.

### Development python environment

If you want to make changes to this repo then you also need to install the tools used for development but which aren't used otherwise, for example pytest.

Run:

`poetry install --with dev`
`poetry run pre-commit install`

### Poetry troubleshooting

If you are running on Windows and see errors about numpy installation errors then it could be an issue with Windows file paths. With default settings, file paths that exceed a few hundred characters can cause installation problems. To overcome this you can either

1) enable long path support in Windows (https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation?tabs=powershell#enable-long-paths-in-windows-10-version-1607-and-later)
2) install python libraries in a folder in the current directory by running `poetry config virtualenvs.in-project true` and then running `poetry install`

## Notes

In keeping with World Bank Group practice, it should be noted that parts of this code base were written with the assistance of ChatGPT.