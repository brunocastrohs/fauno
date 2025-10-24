import { BrowserRouter, Routes, Route } from "react-router-dom";
import Auth from "./features/Auth/index";
import "./_assets/styles/global.css";

import ProtectedLayout from "./features/ProtectedLayout";


function Layers() {
  return <h1 className="section-title">Camadas</h1>;
}
function History() {
  return <h1 className="section-title">Histórico</h1>;
}

export default function App() {
  return (
    <BrowserRouter basename="/fauno">
      <Routes>
        <Route path="/" element={<Auth />} />

        <Route element={<ProtectedLayout />}>
          <Route path="/layers" element={<Layers />} />
          <Route path="/history" element={<History />} />
        </Route>

      </Routes>
    </BrowserRouter>
  );
}
