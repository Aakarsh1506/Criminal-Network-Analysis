import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import CriminalList from "./pages/CriminalList";
import CriminalProfile from "./pages/CriminalProfile";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/search" element={<CriminalList />} />
        <Route path="/criminal/:id" element={<CriminalProfile />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;