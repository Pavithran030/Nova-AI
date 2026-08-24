import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import RecoveryQueue from './pages/RecoveryQueue'
import AuditTrail from './pages/AuditTrail'
import Comparison from './pages/Comparison'
import Strategy from './pages/Strategy'
import './App.css'

function App() {
  return (
    <div className="app-container">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/recovery" element={<RecoveryQueue />} />
          <Route path="/audit" element={<AuditTrail />} />
          <Route path="/comparison" element={<Comparison />} />
          <Route path="/strategy" element={<Strategy />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
