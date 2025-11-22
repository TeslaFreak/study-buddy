import { useState, useEffect } from "react";
import type { SourceMaterial, StudyMaterial } from "../types/chat";
import { getMaterials } from "../services/api";
import "./StudyMaterials.css";

interface StudyMaterialsProps {
  relevantMaterialId?: string;
  sources?: SourceMaterial[];
}

export function StudyMaterials({
  relevantMaterialId,
  sources = [],
}: StudyMaterialsProps) {
  const [activeTab, setActiveTab] = useState<"material" | "sources">(
    "material"
  );
  const [allMaterials, setAllMaterials] = useState<StudyMaterial[]>([]);

  // Fetch materials on mount
  useEffect(() => {
    const fetchMaterials = async () => {
      try {
        const data = await getMaterials();
        setAllMaterials(data.topics);
      } catch (error) {
        console.error("Error fetching materials:", error);
      }
    };
    fetchMaterials();
  }, []);

  // Auto-switch to material tab when we have a relevant material
  useEffect(() => {
    if (relevantMaterialId && allMaterials.length > 0) {
      setActiveTab("material");
    }
  }, [relevantMaterialId, allMaterials]);

  // Find the relevant material
  const relevantMaterial = allMaterials.find(
    (m) => m.id === relevantMaterialId
  );

  // Show empty state if no content
  if (!relevantMaterial && sources.length === 0) {
    return (
      <div className="study-materials-container">
        <div className="empty-state">
          <h3>📚 Study Materials</h3>
          <p>
            Study materials will appear here when you ask questions about
            biology topics.
          </p>
          <p className="hint">
            💡 Try asking about photosynthesis, cellular respiration, or
            mitosis!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="study-materials-container">
      <h3>📚 Study Materials</h3>

      {/* Tab Navigation */}
      <div className="material-tabs">
        {relevantMaterial && (
          <button
            className={`material-tab ${
              activeTab === "material" ? "active" : ""
            }`}
            onClick={() => setActiveTab("material")}
          >
            <span className="tab-icon">📖</span>
            <span className="tab-label">Study Guide</span>
          </button>
        )}
        {sources.length > 0 && (
          <button
            className={`material-tab ${
              activeTab === "sources" ? "active" : ""
            }`}
            onClick={() => setActiveTab("sources")}
          >
            <span className="tab-icon">📄</span>
            <span className="tab-label">
              Source Excerpts ({sources.length})
            </span>
          </button>
        )}
      </div>

      {/* Tab Content */}
      <div className="material-content">
        {activeTab === "material" && relevantMaterial && (
          <StudyGuideContent material={relevantMaterial} />
        )}
        {activeTab === "sources" && sources.length > 0 && (
          <SourceExcerptsContent sources={sources} />
        )}
      </div>
    </div>
  );
}

// Study Guide Tab - Clean, native component
function StudyGuideContent({ material }: { material: StudyMaterial }) {
  return (
    <div className="study-guide">
      <div className="guide-header">
        <div className="guide-meta">
          <span className="guide-category">📂 {material.category}</span>
          <span className="guide-id">ID: {material.id}</span>
        </div>
        <h2 className="guide-title">{material.title}</h2>
      </div>

      <div className="guide-content">
        <p className="guide-text">{material.content}</p>
      </div>

      {material.key_concepts && material.key_concepts.length > 0 && (
        <div className="guide-section">
          <h4 className="section-heading">🔑 Key Concepts</h4>
          <ul className="concepts-list">
            {material.key_concepts.map((concept, idx) => (
              <li key={idx} className="concept-item">
                {concept}
              </li>
            ))}
          </ul>
        </div>
      )}

      {material.study_questions && material.study_questions.length > 0 && (
        <div className="guide-section">
          <h4 className="section-heading">❓ Study Questions</h4>
          <ul className="questions-list">
            {material.study_questions.map((question, idx) => (
              <li key={idx} className="question-item">
                {question}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Source Excerpts Tab - Book-style with ellipses
function SourceExcerptsContent({ sources }: { sources: SourceMaterial[] }) {
  return (
    <div className="source-excerpts">
      <div className="excerpts-intro">
        <p>
          📚 The following excerpts from the course materials were used to
          answer your question:
        </p>
      </div>

      {sources.map((source, idx) => (
        <div key={idx} className="excerpt-card">
          <div className="excerpt-header">
            <span className="excerpt-number">Excerpt {idx + 1}</span>
            <span className="excerpt-relevance">
              {Math.round(source.score * 100)}% relevant
            </span>
          </div>

          <div className="excerpt-body">
            <span className="excerpt-ellipsis">...</span>
            <p className="excerpt-text">{source.content}</p>
            <span className="excerpt-ellipsis">...</span>
          </div>

          <div className="excerpt-footer">
            <span className="excerpt-source">📄 {source.documentName}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
