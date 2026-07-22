---

name: Bug report
description: Create a report to help us improve the package.

body:
    - type: textarea
      attributes:
        label: Describe the Bug
        description: >-
            A clear and concise description of what the bug is.
        validation:
            required: true

    - type: textarea
      attributes:
        label: Expected Behaviour
        description: >-
           A description of what were you expecting to happen.
        validation:
            required: true

    - type: textarea
      attributes:
        label: Steps to Reproduce
        description: >-
            Describe the reproduce to reproduce the bug. 
        placeholder: |
            1. ...
            2. ...
            3. ...

    - type: textarea
      attributes:
        label: Environment Versions
        description: >-
            Describe the environment versions used 
        placeholder: |
            1. OS Type
            2. Python version: `$ python -V`
            3. pip version: `$ pip --version`
            4. pip-tools version: `$ pip-compile --version`
