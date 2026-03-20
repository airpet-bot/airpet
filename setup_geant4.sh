# Setup script for Geant4 v11.4.0
# Add this to ~/.bashrc or source it before running Geant4 examples

export GEANT4_INSTALL=/home/jrenner/projects/software/geant4-install

# Paths
export GEANT4_DIR=${GEANT4_INSTALL}
export PATH=${PATH}:${GEANT4_INSTALL}/bin
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${GEANT4_INSTALL}/lib
export DYLD_LIBRARY_PATH=${DYLD_LIBRARY_PATH}:${GEANT4_INSTALL}/lib  # For macOS if needed

# Data files (physics datasets)
export G4DATA=${GEANT4_INSTALL}/share/Geant4/data
export G4NEUTRONHPDATA=${G4DATA}
export G4PIIData=${G4DATA}
export G4EMLOW=${G4DATA}
export G4NDL=${G4DATA}

# CMake configuration path (needed for find_package(Geant4))
export CMAKE_PREFIX_PATH=${GEANT4_DIR}:${CMAKE_PREFIX_PATH}

echo "Geant4 v11.4.0 environment configured!"
echo "Installation: ${GEANT4_INSTALL}"
echo "Data directory: ${G4DATA}"
