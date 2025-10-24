import { BrowserRouter, Routes, Route } from "react-router-dom";
import Auth from "./features/Auth/index";
import "./_assets/styles/global.css";

export default function App() {
  return (
    <BrowserRouter basename="/fauno">
      <Routes>
        <Route path="/" element={<Auth />} />
        <Route path="/login" element={<Auth />} />
      </Routes>
    </BrowserRouter>
  );
}
