{lib, buildPythonPackage, pytestCheckHook, numpy, pip, pythonOlder }:

buildPythonPackage rec {
    pname = "berpfpy";
    version = "0.0.1"; 
    disabled = pythonOlder "3.10";
    src = ./.;
    format = "pyproject";
    checkInputs = [ pytestCheckHook ];
    buildInputs = [pip]; 
    propagatedBuildInputs  = [ numpy ];
    meta = with lib; {
    };
}

