#ifndef RunAction_h
#define RunAction_h 1

#include "G4UImessenger.hh"
#include "G4UserRunAction.hh"
#include "globals.hh"
#include <set>

// Forward declarations
class G4Run;
class G4UIdirectory;
class G4UIcommand;
class G4UIcmdWithADoubleAndUnit;
class G4UIcmdWithAnInteger;

/// The RunAction class.
///
/// This class is responsible for actions that happen at the beginning and
/// end of a simulation run. Its primary role here is to manage the creation,
/// writing, and closing of the output n-tuple file using G4AnalysisManager.

class RunAction : public G4UserRunAction, public G4UImessenger {
public:
  // The constructor takes a pointer to the EventAction.
  // This allows for communication between the two action classes if needed.
  RunAction();
  virtual ~RunAction();

  // --- G4UserRunAction virtual methods ---
  virtual void BeginOfRunAction(const G4Run *) override;
  virtual void EndOfRunAction(const G4Run *) override;

  virtual void SetNewValue(G4UIcommand *command, G4String newValue) override;

  G4bool GetSaveParticles() const { return fSaveParticles; }
  G4bool GetSaveHits() const { return fSaveHits; }
  G4bool GetSaveHitMetadata() const { return fSaveHitMetadata; }
  G4double GetHitEnergyThreshold() const { return fHitEnergyThreshold; }
  const G4String& GetHitSelectionMode() const { return fHitSelectionMode; }
  const std::set<G4String>& GetHitTargetSensitiveDetectors() const {
    return fHitTargetSensitiveDetectors;
  }
  const std::set<G4String>& GetHitTargetLogicalVolumes() const {
    return fHitTargetLogicalVolumes;
  }
  const std::set<G4String>& GetHitTargetPhysicalVolumes() const {
    return fHitTargetPhysicalVolumes;
  }
  G4int GetHitMinimumMultiplicity() const { return fHitMinimumMultiplicity; }

private:
  G4UIdirectory *fG4petDir;
  G4UIdirectory *fRunDir;
  G4UIcommand *fSaveParticlesCmd;
  G4UIcommand *fSaveHitsCmd;
  G4UIcommand *fSaveHitMetadataCmd;
  G4UIcmdWithADoubleAndUnit *fHitEnergyThresholdCmd;
  G4UIcommand *fHitSelectionModeCmd;
  G4UIcommand *fHitTargetSensitiveDetectorsCmd;
  G4UIcommand *fHitTargetLogicalVolumesCmd;
  G4UIcommand *fHitTargetPhysicalVolumesCmd;
  G4UIcmdWithAnInteger *fHitMinimumMultiplicityCmd;

  G4bool fSaveParticles;
  G4bool fSaveHits;
  G4bool fSaveHitMetadata;
  G4double fHitEnergyThreshold;
  G4String fHitSelectionMode;
  std::set<G4String> fHitTargetSensitiveDetectors;
  std::set<G4String> fHitTargetLogicalVolumes;
  std::set<G4String> fHitTargetPhysicalVolumes;
  G4int fHitMinimumMultiplicity;
};

#endif
