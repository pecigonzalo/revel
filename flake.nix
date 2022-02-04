{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/21.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python39;
        pythonPackages = python.pkgs;
      in
      {
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            python
            pythonPackages.wheel
            pythonPackages.setuptools
          ];
        };
      });
}
