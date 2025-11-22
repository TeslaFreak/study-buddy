import { useState } from "react";
import { Chat } from "./components/Chat";
import { StudyMaterials } from "./components/StudyMaterials";
import type { SourceMaterial } from "./types/chat";
import "./App.css";

function App() {
  const [currentSources, setCurrentSources] = useState<SourceMaterial[]>([]);
  const [relevantMaterialId, setRelevantMaterialId] = useState<
    string | undefined
  >();

  const handleResponseReceived = (
    sources: SourceMaterial[],
    materialId?: string
  ) => {
    if (sources && sources.length > 0) {
      setCurrentSources(sources);
    }

    if (materialId !== undefined && materialId !== null) {
      setRelevantMaterialId(materialId);
    }
  };

  return (
    <div className="app-container">
      <div className="main-content">
        <Chat onResponseReceived={handleResponseReceived} />
      </div>
      <div className="sidebar">
        <StudyMaterials
          relevantMaterialId={relevantMaterialId}
          sources={currentSources}
        />
      </div>
    </div>
  );
}

export default App;
