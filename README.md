# 2023-TQuantum
[![DOI](https://zenodo.org/badge/645860446.svg)](https://zenodo.org/badge/latestdoi/645860446)

Source code for the submission to journal ACM Transactions on Quantum Computing. 

Source code for paper [Improving the Efficiency of Quantum Circuits for
Information Set Decoding](#authors-and-citations) submitted at ACM Transactions
on Quantum Computing. The bibtex is available at the end of the Readme.

This repository is taken from the code available at
[https://github.com/tigerjack/qat-utils](https://github.com/tigerjack/qat-utils)
and can be run on either the open-source [myQLM
simulator](https://github.com/myQLM) or the [QLM
simulator](https://atos.net/en/solutions/quantum-learning-machine), both
provided by Atos.

# Installation #
If you would like to test the code and you don not have access to a QLM, you can
install the open source
[myQLM](https://myqlm.github.io/myqlm_specific/install.html).

The best way to install the code would be through
[pyenv](https://github.com/pyenv/pyenv) and the
[pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv). Refer to their
guides on how to install them. After both of them are installed, you can run.

```
pyenv install 3.9.7
pyenv virtualenv 3.9.7 myqlm_env
```

where `3.9.7` is the python version used for this code and `myqlm_env` is the
name of the virtual environment (you can change whatever name you like). You can
also try for different python version, but the code has not been tested with
them. You can check the python versions available for myQLM on their
[documentation](https://myqlm.github.io/myqlm_specific/install.html).

Then, you can install myQLM inside the environment by launching

```
pyenv activate myqlm_env
pip install myqlm
pip install nptyping sympy
pip install paramaterized
```

`nptyping` is used to get dynamic hints for numpy. `sympy`, up to now, is only
used to automatically compute the RREF of a matrix. `parameterized` is required
by most of the unit tests in order to have a great refactoring of code.

Then, you can clone this repository and activate the environment.

```
cd <SOME_DIR>
git clone https://github.com/tigerjack/qat-utils.git
cd qat-utils
pyenv activate myqlm_env
```

where `<SOME_DIR>` can be whatever directory you want this repository to be
contained in.


# Tests #
The tests can be run using `python -m unittest` (all tests) or `python -m
unittest test.module_name` (only a specific test case, replacing module name
with the actual name of the module). For example, if you want to run all the
tests related to the RREF circuit, go to the root directory and run `python -m
unittest test.test_qroutine_rref`.

When launching tests, you can provide some optional environment variables

  * `LOG_LEVEL`, with values equal to the names provided by Python logging
utilities. E.g. `LOG_LEVEL=DEBUG python -m unittest test.test_qroutine_rref`.
  * `SLOW_TEST_ON=1` to enable also time consuming tests 
  * `QLM_ON=1` to use the QLM instead of myQLM
  * `SIMULATOR`, to pass the name of a simulator. For myQLM, only the `pylinalg`
    simulator is actually available. For QLM, there are a variety of available
    simulators depending on the version.


# Contribution Guidelines #
If you would like to contribute to the code, please open a [GitHub
issue](https://github.com/tigerjack/qat-utils/issues) on the original [qat-utils
repository](https://github.com/tigerjack/qat-utils). This repository will be
made read-only after the conference and it is here just for reference.

# Authors and citations #
The code here was used in the results of the following articles

[PeBP23] _Perriello, Simone_ ; Barenghi, Alessandro ; Pelosi, Gerardo: /Improving
the efficiency of quantum circuits for information set decoding/. In: ACM
Transactions on Quantum Computing. New York, NY, USA, Association for Computing
Machinery (2023). — Citation Key: 10.1145/3607256 
[Accepted on June 2023]
[bibtex](/bibtex.bib)
