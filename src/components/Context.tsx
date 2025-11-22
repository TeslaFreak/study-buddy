import { useState } from "react";
import type { SourceMaterial } from "../types/chat";
import "./Context.css";

interface ContextProps {
  sources: SourceMaterial[];
}

interface ParsedJsonContent {
  id?: string;
  title?: string;
  content?: string;
  key_concepts?: string[];
  study_questions?: string[];
  category?: string;
}

export function Context({ sources }: ContextProps) {
  const [activeTab, setActiveTab] = useState<number>(0);

  // Intelligent content parser - detects JSON and extracts meaningful content
  const parseContent = (content: string) => {
    // Check if it's JSON content
    if (content.trim().startsWith("{") || content.trim().startsWith("[")) {
      try {
        const parsed = JSON.parse(content);

        // Handle case where the entire materials.json structure is returned
        if (parsed.topics && Array.isArray(parsed.topics)) {
          // If only one topic in array, return it directly
          if (parsed.topics.length === 1) {
            return {
              type: "json" as const,
              data: parsed.topics[0],
            };
          }

          // Multiple topics - return all for user to choose
          // This happens when KB returns the full file with no chunking
          return {
            type: "json-topics" as const,
            data: parsed.topics,
          };
        }

        // Handle single topic object (when KB chunks properly or returns one topic)
        if (parsed.title && parsed.content) {
          return {
            type: "json" as const,
            data: parsed,
          };
        }

        // Fallback: show formatted JSON
        return {
          type: "json-raw" as const,
          data: parsed,
        };
      } catch {
        // Not valid JSON, treat as text
      }
    }

    // PDF or plain text content
    return {
      type: "text" as const,
      data: content,
    };
  };

  // Render JSON content in a structured, readable format
  const renderJsonContent = (data: ParsedJsonContent) => {
    return (
      <div className="json-content">
        {data.id && <div className="content-id">🔖 ID: {data.id}</div>}

        {data.category && (
          <div className="content-category">📂 {data.category}</div>
        )}

        {data.title && <h4 className="content-title">{data.title}</h4>}

        {data.content && (
          <div className="content-body">
            <p>{data.content}</p>
          </div>
        )}

        {data.key_concepts && data.key_concepts.length > 0 && (
          <div className="content-section">
            <h5>🔑 Key Concepts</h5>
            <ul className="concepts-list">
              {data.key_concepts.map((concept, idx) => (
                <li key={idx}>{concept}</li>
              ))}
            </ul>
          </div>
        )}

        {data.study_questions && data.study_questions.length > 0 && (
          <div className="content-section">
            <h5>❓ Study Questions</h5>
            <ul className="questions-list">
              {data.study_questions.map((question, idx) => (
                <li key={idx}>{question}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  // Render multiple topics from full materials.json
  const renderTopicsList = (topics: ParsedJsonContent[]) => {
    return (
      <div className="topics-list">
        <p className="topics-intro">
          This material contains multiple topics. Here are all available topics:
        </p>
        {topics.map((topic, idx) => (
          <div key={topic.id || idx} className="topic-card">
            {topic.id && <div className="topic-id">🔖 {topic.id}</div>}
            {topic.category && (
              <div className="topic-category">📂 {topic.category}</div>
            )}
            {topic.title && <h5 className="topic-title">{topic.title}</h5>}
            {topic.content && (
              <p className="topic-preview">
                {topic.content.slice(0, 200)}
                {topic.content.length > 200 ? "..." : ""}
              </p>
            )}
          </div>
        ))}
      </div>
    );
  };

  // Render PDF text with better formatting - FULL WIDTH
  const renderTextContent = (text: string) => {
    const cleanText = text.replace(/\s+/g, " ").trim();
    const sentences = cleanText.match(/[^.!?]+[.!?]+/g) || [cleanText];

    const paragraphs: string[] = [];
    let currentParagraph: string[] = [];

    sentences.forEach((sentence) => {
      const trimmedSentence = sentence.trim();
      const isHeading =
        /^[A-Z\s]{5,60}:?\s*$/.test(trimmedSentence) ||
        trimmedSentence.endsWith(":");
      const isBullet = /^[✓•\-\*]/.test(trimmedSentence);
      const shouldBreak = currentParagraph.length >= 3 || isHeading || isBullet;

      if (shouldBreak && currentParagraph.length > 0) {
        paragraphs.push(currentParagraph.join(" "));
        currentParagraph = [];
      }
      currentParagraph.push(trimmedSentence);
    });

    if (currentParagraph.length > 0) {
      paragraphs.push(currentParagraph.join(" "));
    }

    return (
      <div className="material-text">
        {paragraphs.map((paragraph, idx) => {
          const trimmed = paragraph.trim();
          const isHeading =
            /^[A-Z\s]{5,60}:?\s*$/.test(trimmed) ||
            (trimmed.length < 80 && trimmed.endsWith(":"));

          if (isHeading) {
            return (
              <h4 key={idx} className="material-heading">
                {trimmed}
              </h4>
            );
          }

          if (/^[✓•\-\*]\s/.test(trimmed)) {
            return (
              <div key={idx} className="material-bullet">
                {trimmed.replace(/^[✓•\-\*]\s/, "")}
              </div>
            );
          }

          return (
            <p key={idx} className="material-paragraph">
              {trimmed}
            </p>
          );
        })}
      </div>
    );
  };

  // Render raw JSON with syntax highlighting
  const renderRawJson = (data: unknown) => {
    return (
      <pre className="json-raw">
        <code>{JSON.stringify(data, null, 2)}</code>
      </pre>
    );
  };

  if (sources.length === 0) {
    return (
      <div className="context-container">
        <div className="empty-state">
          <h3>📚 Study Materials</h3>
          <p>
            Supplemental reading materials will appear here when Study Buddy
            retrieves them to help answer your questions.
          </p>
          <p className="hint">
            💡 Try asking about photosynthesis, cellular respiration, or
            mitosis!
          </p>
        </div>
      </div>
    );
  }

  const activeMaterial = sources[activeTab];
  const parsed = parseContent(activeMaterial.content);

  return (
    <div className="context-container">
      <h3>📚 Study Materials</h3>

      {/* Material Tabs */}
      <div className="material-tabs">
        {sources.map((source, index) => (
          <button
            key={index}
            className={`material-tab ${activeTab === index ? "active" : ""}`}
            onClick={() => setActiveTab(index)}
            title={source.documentName}
          >
            <span className="tab-icon">📄</span>
            <span className="tab-name">{source.documentName}</span>
          </button>
        ))}
      </div>

      {/* Active Material Content - Full Width */}
      <div className="material-content">
        {parsed.type === "json" && renderJsonContent(parsed.data)}
        {parsed.type === "json-topics" && renderTopicsList(parsed.data)}
        {parsed.type === "text" && renderTextContent(parsed.data)}
        {parsed.type === "json-raw" && renderRawJson(parsed.data)}

        <div className="material-footer">
          <div className="relevance-info">
            <span className="relevance-icon">✓</span>
            <span>
              {Math.round(activeMaterial.score * 100)}% relevant to your
              question
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
