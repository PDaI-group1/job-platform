import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import "./App.css";
import JobsPage from "./pages/jobs_page";
import JobDetailsPage from "./pages/job_details_page";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/jobs" replace />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:id" element={<JobDetailsPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
