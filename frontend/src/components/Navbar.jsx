import { NavLink, useNavigate } from "react-router-dom";
import { logout } from "../api/auth";
import "./Navbar.css";

const NAV_LINKS = [
  { label: "Home", path: "/dashboard" },
  { label: "Criminal List", path: "/criminal-list" },
  { label: "Upload Doc", path: "/upload" },
];

function Navbar() {
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">CNA</span>
        <span className="navbar-title">Criminal Network Analysis</span>
      </div>

      <ul className="navbar-links">
        {NAV_LINKS.map((link) => (
          <li key={link.path}>
            <NavLink
              to={link.path}
              className={({ isActive }) =>
                isActive ? "navbar-link active" : "navbar-link"
              }
            >
              {link.label}
            </NavLink>
          </li>
        ))}
        <li>
          <button type="button" className="navbar-logout" onClick={handleLogout}>
            Log out
          </button>
        </li>
      </ul>
    </nav>
  );
}

export default Navbar;