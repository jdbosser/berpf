{lib, buildPythonPackage, pytestCheckHook, numpy, pip, setuptools, pythonOlder }:

buildPythonPackage rec {
    pname = "berpf";
    version = "0.0.1"; 
    disabled = pythonOlder "3.10";
    src = ./.;
    format = "pyproject";
    checkInputs = [ pytestCheckHook ];
    buildInputs = [pip setuptools]; 
    propagatedBuildInputs  = [ numpy ];
    meta = with lib; {
    };
}

