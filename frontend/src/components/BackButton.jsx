import { useNavigate } from "react-router-dom";
import "./BackButton.css";

function BackButton({ to = "/dashboard", label = "← Back to dashboard" }) {
  const navigate = useNavigate();
  return (
    <button className="back-button" onClick={() => navigate(to)}>
      {label}
    </button>
  );
}

export default BackButton;