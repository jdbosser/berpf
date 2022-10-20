{
  description = "A very basic flake";

    
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.05";
    flakeutils.url = "github:numtide/flake-utils";
    render-anim.url = "github:jdbosser/render-anim";
    render-anim.flake = false;
  };


  outputs = { self, nixpkgs, flakeutils, render-anim }: 
    flakeutils.lib.eachDefaultSystem (system:
        let pkgs = nixpkgs.legacyPackages.${system}; 
        
        in
        rec {
            devShells.default =  pkgs.mkShell {
                  buildInputs = [
                    (pkgs.python310.withPackages (p: [
                        p.numpy 
                        p.matplotlib 
                        p.setuptools
                        p.scipy 
                        p.tqdm
                        p.mypy
                        packages.default
                        p.pytest
                    ]))
                    pkgs.pyright
                  ];
            };

            packages.default = pkgs.python310Packages.callPackage ./pack.nix {}; 

        }
    ) // {

        buildPythonPackage = (python: python.pkgs.callPackage ./pack.nix {}); 

    };
}
