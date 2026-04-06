#include "DetectorConstruction.hh"
#include "AirPetSensitiveDetector.hh"

#include "G4FieldManager.hh"
#include "G4GlobalMagFieldMessenger.hh"
#include "G4RunManager.hh"
#include "G4GenericMessenger.hh"
#include "G4UIdirectory.hh"
#include "G4UIcommand.hh"
#include "G4UIparameter.hh"
#include "G4UIcmdWithAString.hh"
#include "G4SDManager.hh"
#include "G4UniformMagField.hh"
#include "G4LogicalVolumeStore.hh"
#include "G4SolidStore.hh"
#include "G4PhysicalVolumeStore.hh"
#include "G4GeometryManager.hh"

#include <sstream>

DetectorConstruction::DetectorConstruction()
 : G4VUserDetectorConstruction(),
   fWorldVolume(nullptr),
   fMessenger(nullptr),
   fMagFieldMessenger(nullptr),
   fGDMLFilename("default.gdml") // A default name
{
  // The G4GDMLParser can be configured to check for overlaps
  fParser.SetOverlapCheck(true);
  fMagFieldMessenger = new G4GlobalMagFieldMessenger(G4ThreeVector());
  DefineCommands();
}

DetectorConstruction::~DetectorConstruction()
{
  delete fMagFieldMessenger;
  delete fMessenger;
}

void DetectorConstruction::DefineCommands()
{

  // The G4GenericMessenger ties UI commands to methods of this class.
  // The 'this' pointer is passed here.
  fMessenger = new G4GenericMessenger(this, "/g4pet/detector/", "Detector control");

  // Command to read a GDML file
  fMessenger->DeclareMethod("readFile", &DetectorConstruction::SetGDMLFile)
      .SetGuidance("Read geometry from a GDML file.")
      .SetParameterName("filename", false) // The name for the one and only parameter
      .SetStates(G4State_PreInit, G4State_Idle)
      .SetToBeBroadcasted(false);

  // Command to add a Sensitive Detector to a Logical Volume
  fMessenger->DeclareMethod("addSD", &DetectorConstruction::SetSensitiveDetector)
      .SetGuidance("Assign a sensitive detector to a logical volume.")
      .SetGuidance("Usage: /g4pet/detector/addSD <LogicalVolumeName> <SensitiveDetectorName>")
      .SetParameterName("LogicalVolumeName",     /*omittable=*/false)
      .SetParameterName("SensitiveDetectorName", /*omittable=*/false)
      .SetStates(G4State_PreInit, G4State_Idle)
      .SetToBeBroadcasted(false);

  // Command to add a local magnetic field to a Logical Volume
  fMessenger->DeclareMethod("addLocalMagField", &DetectorConstruction::SetLocalMagneticField)
      .SetGuidance("Assign a local uniform magnetic field to a logical volume.")
      .SetGuidance("Usage: /g4pet/detector/addLocalMagField <LogicalVolumeName>|<FieldX>|<FieldY>|<FieldZ>")
      .SetParameterName("Assignment", /*omittable=*/false)
      .SetStates(G4State_PreInit, G4State_Idle)
      .SetToBeBroadcasted(false);
}

// This method is defined for the messenger (takes G4Strings)
void DetectorConstruction::SetSensitiveDetector(G4String logicalVolumeName, G4String sdName)
{
  fSensitiveDetectorsMap[logicalVolumeName] = sdName;
  G4cout << "--> Requested sensitive detector '" << sdName
         << "' for logical volume '" << logicalVolumeName << "'" << G4endl;

  // Tell the RunManager that the detector setup has changed and needs to be rebuilt.
  // This will ensure ConstructSDandField() is called again before the next run.
  //G4RunManager::GetRunManager()->ReinitializeGeometry();
}

void DetectorConstruction::SetLocalMagneticField(G4String assignmentPayload)
{
  std::stringstream stream(assignmentPayload);
  std::string logicalVolumeName;
  std::string fieldXText;
  std::string fieldYText;
  std::string fieldZText;

  if (!std::getline(stream, logicalVolumeName, '|') ||
      !std::getline(stream, fieldXText, '|') ||
      !std::getline(stream, fieldYText, '|') ||
      !std::getline(stream, fieldZText, '|')) {
    G4cerr << "--> WARNING: Invalid local magnetic field payload '"
           << assignmentPayload
           << "'. Expected <LogicalVolumeName>|<FieldX>|<FieldY>|<FieldZ>." << G4endl;
    return;
  }

  try {
    const G4double fieldX = std::stod(fieldXText);
    const G4double fieldY = std::stod(fieldYText);
    const G4double fieldZ = std::stod(fieldZText);

    fLocalMagFieldAssignments[logicalVolumeName] = G4ThreeVector(fieldX, fieldY, fieldZ);
    G4cout << "--> Requested local magnetic field ("
           << fieldX << ", " << fieldY << ", " << fieldZ
           << ") tesla for logical volume '" << logicalVolumeName << "'" << G4endl;
  } catch (const std::exception&) {
    G4cerr << "--> WARNING: Invalid numeric local magnetic field payload '"
           << assignmentPayload
           << "'. Expected <LogicalVolumeName>|<FieldX>|<FieldY>|<FieldZ>." << G4endl;
  }
}

void DetectorConstruction::SetGDMLFile(G4String filename)
{
  // Check if the file exists before storing the name
  std::ifstream ifile(filename);
  if (!ifile) {
    G4Exception("DetectorConstruction::SetGDMLFile",
                "InvalidFileName", FatalException,
                ("GDML file not found: " + filename).c_str());
    fGDMLFilename = "";
    return;
  }

  fGDMLFilename = filename;
  G4cout << "--> Geometry will be loaded from: " << fGDMLFilename << G4endl;

  // Inform the RunManager that the geometry needs to be rebuilt
  //G4RunManager::GetRunManager()->ReinitializeGeometry();
  //G4cout << "--> Geometry will be loaded from: " << fGDMLFilename << G4endl;
}

G4VPhysicalVolume* DetectorConstruction::Construct()
{
  if (fGDMLFilename.empty()) {
    G4Exception("DetectorConstruction::Construct()",
                "NoGDMLFile", FatalException,
                "No GDML file specified. Use /g4pet/detector/readFile to set one.");
    return nullptr;
  }

  // Clear any previously loaded geometry
  G4GeometryManager::GetInstance()->OpenGeometry();
  G4PhysicalVolumeStore::GetInstance()->Clean();
  G4LogicalVolumeStore::GetInstance()->Clean();
  G4SolidStore::GetInstance()->Clean();

  // Parse the GDML file
  // The parser will create all materials, solids, and logical/physical volumes.
  fParser.Read(fGDMLFilename, false); // false = do not validate schema

  // Get the pointer to the world volume
  fWorldVolume = fParser.GetWorldVolume();

  if (!fWorldVolume) {
    G4Exception("DetectorConstruction::Construct()",
                "WorldVolumeNotFound", FatalException,
                "Could not find the World Volume in the GDML file.");
  }

  return fWorldVolume;
}

void DetectorConstruction::ConstructSDandField()
{

  G4cout << G4endl << "-------- DetectorConstruction::ConstructSDandField --------" << G4endl;
  
  G4SDManager* sdManager = G4SDManager::GetSDMpointer();
  G4LogicalVolumeStore* lvStore = G4LogicalVolumeStore::GetInstance();
  fLocalMagneticFields.clear();
  fLocalFieldManagers.clear();
  
  // Iterate over all the SD attachment requests made via the messenger
  //G4cout << "--> Sensitve det map contains " << fSensitiveDetectorsMap.size() << " detector" << G4endl;
  for (const auto& pair : fSensitiveDetectorsMap) {
    const G4String& lvName = pair.first;
    const G4String& sdName = pair.second;

    G4LogicalVolume* logicalVolume = lvStore->GetVolume(lvName);

    if (!logicalVolume) {
      G4cerr << "--> WARNING: Logical Volume '" << lvName
             << "' not found in geometry. Cannot attach SD '"
             << sdName << "'." << G4endl;
      continue;
    }

    // Check if the SD already exists
    G4VSensitiveDetector* existingSD = sdManager->FindSensitiveDetector(sdName, false); // false = don't warn if not found

    if (existingSD) {
      // Use the base class's method to attach the SD
      G4VUserDetectorConstruction::SetSensitiveDetector(logicalVolume, existingSD);
      G4cout << "--> Attached existing sensitive detector '" << sdName
             << "' to logical volume '" << lvName << "'" << G4endl;
    }
    else {
      // If it doesn't exist, create a new instance of our generic SD
      auto* airpetSD = new AirPetSensitiveDetector(sdName);
      sdManager->AddNewDetector(airpetSD);
      // Use the base class's method to attach the SD
      G4VUserDetectorConstruction::SetSensitiveDetector(logicalVolume, airpetSD);
      G4cout << "--> Created and attached new sensitive detector '" << sdName
             << "' to logical volume '" << lvName << "'" << G4endl;
    }
  }

  for (const auto& pair : fLocalMagFieldAssignments) {
    const G4String& lvName = pair.first;
    const G4ThreeVector& fieldVector = pair.second;

    G4LogicalVolume* logicalVolume = lvStore->GetVolume(lvName);

    if (!logicalVolume) {
      G4cerr << "--> WARNING: Logical Volume '" << lvName
             << "' not found in geometry. Cannot attach local magnetic field ("
             << fieldVector.x() << ", " << fieldVector.y() << ", " << fieldVector.z()
             << ") tesla." << G4endl;
      continue;
    }

    auto localField = std::make_unique<G4UniformMagField>(fieldVector);
    auto fieldManager = std::make_unique<G4FieldManager>(localField.get());
    logicalVolume->SetFieldManager(fieldManager.get(), false);

    G4cout << "--> Attached local magnetic field ("
           << fieldVector.x() << ", " << fieldVector.y() << ", " << fieldVector.z()
           << ") tesla to logical volume '" << lvName << "'" << G4endl;

    fLocalMagneticFields.push_back(std::move(localField));
    fLocalFieldManagers.push_back(std::move(fieldManager));
  }
}
