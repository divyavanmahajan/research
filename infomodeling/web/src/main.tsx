import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Route, Routes, Navigate } from 'react-router-dom'
import Upload from './pages/Upload'
import Explorer from './pages/Explorer'
import Graph from './pages/Graph'
import Preview from './pages/Preview'
import Seeds from './pages/Seeds'
import Download from './pages/Download'
import Nav from './components/Nav'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Nav />
      <main style={{ padding: '1.5rem' }}>
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/explorer" element={<Explorer />} />
          <Route path="/graph" element={<Graph />} />
          <Route path="/preview" element={<Preview />} />
          <Route path="/seeds" element={<Seeds />} />
          <Route path="/download" element={<Download />} />
        </Routes>
      </main>
    </BrowserRouter>
  </React.StrictMode>,
)
