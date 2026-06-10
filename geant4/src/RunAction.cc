#include "RunAction.hh"
#include "EventAction.hh"
#include "G4AnalysisManager.hh"
#include "G4Run.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4UIcmdWithADoubleAndUnit.hh"
#include "G4UIcmdWithAnInteger.hh"
#include "G4UIcommand.hh"
#include "G4UIdirectory.hh"
#include "G4UIparameter.hh"
#include <sstream>

namespace {
std::set<G4String> ParseCommaSeparatedNames(const G4String& rawValue) {
  std::set<G4String> names;
  std::stringstream stream(rawValue);
  std::string item;
  while (std::getline(stream, item, ',')) {
    const auto first = item.find_first_not_of(" \t");
    if (first == std::string::npos) continue;
    const auto last = item.find_last_not_of(" \t");
    names.insert(item.substr(first, last - first + 1));
  }
  return names;
}
}

RunAction::RunAction()
    : G4UserRunAction(), fSaveParticles(false), fSaveHits(true), fSaveHitMetadata(true),
      fHitEnergyThreshold(0.0), fHitSelectionMode("all_hits"),
      fHitMinimumMultiplicity(1) {
  auto analysisManager = G4AnalysisManager::Instance();
  analysisManager->SetDefaultFileType("hdf5");
  analysisManager->SetVerboseLevel(1);
  fG4petDir = new G4UIdirectory("/g4pet/");
  fRunDir = new G4UIdirectory("/g4pet/run/");
  fSaveParticlesCmd = new G4UIcommand("/g4pet/run/saveParticles", this);
  fSaveParticlesCmd->SetParameter(new G4UIparameter("value", 'b', true));
  fSaveParticlesCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fSaveHitsCmd = new G4UIcommand("/g4pet/run/saveHits", this);
  fSaveHitsCmd->SetParameter(new G4UIparameter("value", 'b', true));
  fSaveHitsCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fSaveHitMetadataCmd = new G4UIcommand("/g4pet/run/saveHitMetadata", this);
  fSaveHitMetadataCmd->SetParameter(new G4UIparameter("value", 'b', true));
  fSaveHitMetadataCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fHitEnergyThresholdCmd = new G4UIcmdWithADoubleAndUnit("/g4pet/run/hitEnergyThreshold", this);
  fHitEnergyThresholdCmd->SetParameterName("energy", true);
  fHitEnergyThresholdCmd->SetDefaultValue(0.0);
  fHitEnergyThresholdCmd->SetUnitCategory("Energy");
  fHitEnergyThresholdCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fHitSelectionModeCmd = new G4UIcommand("/g4pet/run/hitSelectionMode", this);
  fHitSelectionModeCmd->SetParameter(new G4UIparameter("mode", 's', false));
  fHitSelectionModeCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fHitTargetSensitiveDetectorsCmd =
      new G4UIcommand("/g4pet/run/hitTargetSensitiveDetectors", this);
  fHitTargetSensitiveDetectorsCmd->SetParameter(new G4UIparameter("names", 's', true));
  fHitTargetSensitiveDetectorsCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fHitTargetLogicalVolumesCmd =
      new G4UIcommand("/g4pet/run/hitTargetLogicalVolumes", this);
  fHitTargetLogicalVolumesCmd->SetParameter(new G4UIparameter("names", 's', true));
  fHitTargetLogicalVolumesCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fHitTargetPhysicalVolumesCmd =
      new G4UIcommand("/g4pet/run/hitTargetPhysicalVolumes", this);
  fHitTargetPhysicalVolumesCmd->SetParameter(new G4UIparameter("names", 's', true));
  fHitTargetPhysicalVolumesCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
  fHitMinimumMultiplicityCmd =
      new G4UIcmdWithAnInteger("/g4pet/run/hitMinimumMultiplicity", this);
  fHitMinimumMultiplicityCmd->SetParameterName("count", false);
  fHitMinimumMultiplicityCmd->SetRange("count>=1");
  fHitMinimumMultiplicityCmd->AvailableForStates(G4State_PreInit, G4State_Idle);
}

RunAction::~RunAction() {}

void RunAction::SetNewValue(G4UIcommand *command, G4String newValue) {
  if (command == fSaveParticlesCmd) {
    fSaveParticles = G4UIcommand::ConvertToBool(newValue);
  } else if (command == fSaveHitsCmd) {
    fSaveHits = G4UIcommand::ConvertToBool(newValue);
  } else if (command == fSaveHitMetadataCmd) {
    fSaveHitMetadata = G4UIcommand::ConvertToBool(newValue);
  } else if (command == fHitEnergyThresholdCmd) {
    fHitEnergyThreshold = fHitEnergyThresholdCmd->GetNewDoubleValue(newValue);
  } else if (command == fHitSelectionModeCmd) {
    if (newValue == "all_hits" || newValue == "target_hits_only" ||
        newValue == "triggered_events") {
      fHitSelectionMode = newValue;
    } else {
      G4cerr << "--> WARNING: Unknown hit selection mode '" << newValue
             << "'. Keeping '" << fHitSelectionMode << "'." << G4endl;
    }
  } else if (command == fHitTargetSensitiveDetectorsCmd) {
    fHitTargetSensitiveDetectors = ParseCommaSeparatedNames(newValue);
  } else if (command == fHitTargetLogicalVolumesCmd) {
    fHitTargetLogicalVolumes = ParseCommaSeparatedNames(newValue);
  } else if (command == fHitTargetPhysicalVolumesCmd) {
    fHitTargetPhysicalVolumes = ParseCommaSeparatedNames(newValue);
  } else if (command == fHitMinimumMultiplicityCmd) {
    fHitMinimumMultiplicity = fHitMinimumMultiplicityCmd->GetNewIntValue(newValue);
  }
}

void RunAction::BeginOfRunAction(const G4Run * /*aRun*/) {
  auto analysisManager = G4AnalysisManager::Instance();
  G4cout << "--> RunAction::BeginOfRunAction: Opening output.hdf5" << G4endl;
  analysisManager->OpenFile("output.hdf5");
  if (fSaveParticles) {
    analysisManager->CreateNtuple("Tracks", "Particle Trajectories");
    analysisManager->CreateNtupleIColumn("EventID");
    analysisManager->CreateNtupleSColumn("ParticleName");
    analysisManager->CreateNtupleIColumn("TrackID");
    analysisManager->CreateNtupleIColumn("ParentID");
    analysisManager->CreateNtupleDColumn("Mass");
    analysisManager->CreateNtupleDColumn("InitialPosX");
    analysisManager->CreateNtupleDColumn("InitialPosY");
    analysisManager->CreateNtupleDColumn("InitialPosZ");
    analysisManager->CreateNtupleDColumn("InitialTime");
    analysisManager->CreateNtupleDColumn("FinalPosX");
    analysisManager->CreateNtupleDColumn("FinalPosY");
    analysisManager->CreateNtupleDColumn("FinalPosZ");
    analysisManager->CreateNtupleDColumn("FinalTime");
    analysisManager->CreateNtupleDColumn("InitialMomX");
    analysisManager->CreateNtupleDColumn("InitialMomY");
    analysisManager->CreateNtupleDColumn("InitialMomZ");
    analysisManager->CreateNtupleDColumn("FinalMomX");
    analysisManager->CreateNtupleDColumn("FinalMomY");
    analysisManager->CreateNtupleDColumn("FinalMomZ");
    analysisManager->CreateNtupleSColumn("InitialVolume");
    analysisManager->CreateNtupleSColumn("FinalVolume");
    analysisManager->CreateNtupleSColumn("CreatorProcess");
    analysisManager->FinishNtuple(0);
  }
  if (fSaveHits) {
    G4int hits_ntuple_ID = fSaveParticles ? 1 : 0;
    analysisManager->CreateNtuple("Hits", "Sensitive Detector Hits");
    analysisManager->CreateNtupleIColumn("EventID");
    analysisManager->CreateNtupleDColumn("Edep");
    analysisManager->CreateNtupleDColumn("PosX");
    analysisManager->CreateNtupleDColumn("PosY");
    analysisManager->CreateNtupleDColumn("PosZ");
    analysisManager->CreateNtupleDColumn("Time");
    if (fSaveHitMetadata) {
      analysisManager->CreateNtupleSColumn("SensitiveDetectorName");
      analysisManager->CreateNtupleSColumn("LogicalVolumeName");
      analysisManager->CreateNtupleSColumn("PhysicalVolumeName");
      analysisManager->CreateNtupleIColumn("CopyNo");
      analysisManager->CreateNtupleSColumn("ParticleName");
      analysisManager->CreateNtupleIColumn("TrackID");
      analysisManager->CreateNtupleIColumn("ParentID");
    }
    analysisManager->FinishNtuple(hits_ntuple_ID);
  }
}

void RunAction::EndOfRunAction(const G4Run * /*aRun*/) {
  auto analysisManager = G4AnalysisManager::Instance();
  G4cout << "--> RunAction::EndOfRunAction: Writing and Closing..." << G4endl;
  analysisManager->Write();
  analysisManager->CloseFile();
}
