import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import Navbar from "./components/Navbar";
import RequireAuth from "./components/RequireAuth";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import CriminalList from "./pages/CriminalList";
import CriminalProfile from "./pages/CriminalProfile";
import UploadDoc from "./pages/UploadDoc";
import DocumentReview from "./pages/DocumentReview";
import CriminalListPage from "./pages/CriminalListPage";
import AdminPanel from "./pages/AdminPanel";
import InvestigatorAnalysis from "./pages/InvestigatorAnalysis";
import "./App.css";

const NO_NAVBAR_PATHS = ["/", "/login", "/admin"];

function AppLayout() {
  const location = useLocation();
  const showNavbar = !NO_NAVBAR_PATHS.includes(location.pathname);

  return (
    <>
      {showNavbar && <Navbar />}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />

        <Route element={<RequireAuth />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/search" element={<CriminalList />} />
          <Route path="/criminal/:id" element={<CriminalProfile />} />
          <Route path="/analysis/:id" element={<InvestigatorAnalysis />} />
          <Route path="/upload" element={<UploadDoc />} />
          <Route path="/documents/:id/review" element={<DocumentReview />} />
          <Route path="/criminal-list" element={<CriminalListPage />} />
          <Route path="/admin" element={<AdminPanel />} />
        </Route>
      </Routes>
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

export default App;
