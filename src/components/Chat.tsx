import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Message, SourceMaterial } from "../types/chat";
import { sendMessage } from "../services/api";
import "./Chat.css";

interface ChatProps {
  onResponseReceived: (sources: SourceMaterial[], materialId?: string) => void;
}

export function Chat({ onResponseReceived }: ChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage(userMessage.content);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.response,
        timestamp: new Date(),
        sources: response.sources,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      onResponseReceived(response.sources || [], response.relevantMaterialId);
    } catch (err) {
      setError("Failed to send message. Please try again.");
      console.error("Chat error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Study Buddy Chat</h2>
        <p>Ask questions about biology topics!</p>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>
              No messages yet. Try asking about photosynthesis, cellular
              respiration, or mitosis! Or ask to test your knowledge on the
              subjects
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <div key={message.id} className={`message message-${message.role}`}>
              <div className="message-role">
                {message.role === "user" ? "You" : "Study Buddy"}
              </div>
              <div className="message-content">
                {message.role === "assistant" ? (
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                ) : (
                  message.content
                )}
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="message message-assistant">
            <div className="message-role">Study Buddy</div>
            <div className="message-content loading">Thinking...</div>
          </div>
        )}
        {error && <div className="error-message">{error}</div>}
      </div>

      <div className="input-container">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && !isLoading && handleSend()}
          placeholder="Ask a question about your study materials..."
          disabled={isLoading}
          className="chat-input"
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !inputValue.trim()}
          className="send-button"
        >
          {isLoading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}
