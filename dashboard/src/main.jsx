import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const timestamp = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium', timeStyle: 'medium',
});

function JobTable({ jobs }) {
  if (!jobs.length) return <p className="message">No oven jobs have been saved.</p>;
  return (
    <div className="table-scroll" role="region" aria-label="Saved oven jobs" tabIndex={0}>
      <table>
        <thead>
          <tr>{['Job', 'Oven serial', 'Model', 'Mode', 'Program', 'Starting settings', 'Started', 'Stopped']
            .map((heading) => <th key={heading} scope="col">{heading}</th>)}</tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.job_id}>
              <th scope="row">#{job.job_id}</th>
              <td>{job.serial_number}</td>
              <td>{job.model_number || '—'}</td>
              <td><span className="mode">{job.mode}</span></td>
              <td>{job.job_file || '—'}</td>
              <td><details>
                <summary>{job.mode === 'MANUAL'
                  ? `${job.job_settings.duration_seconds ?? '—'} s · ${job.job_settings.power_percent ?? '—'}%`
                  : 'View settings'}</summary>
                <pre>{JSON.stringify(job.job_settings, null, 2)}</pre>
              </details></td>
              <td>{timestamp.format(new Date(job.start_time))}</td>
              <td>{job.stop_time ? timestamp.format(new Date(job.stop_time)) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Dashboard() {
  const [authorization, setAuthorization] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [next, setNext] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function load(token, before) {
    setBusy(true);
    setError('');
    try {
      const query = before ? `?before=${encodeURIComponent(before)}` : '';
      const response = await fetch(`/api/oven-dashboard/jobs${query}`, {
        headers: { Authorization: token },
        cache: 'no-store',
      });
      if (response.status === 401) {
        setAuthorization(null);
        setJobs([]);
        setNext(null);
        throw new Error('The dashboard username or password was rejected.');
      }
      if (!response.ok) throw new Error(`Could not load oven jobs (HTTP ${response.status}).`);
      const page = await response.json();
      setAuthorization(token);
      setJobs((previous) => before ? [...previous, ...page.jobs] : page.jobs);
      setNext(page.next_before);
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  function signIn(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const username = form.get('username');
    const password = form.get('password');
    if (username.includes(':') || !/^[ -~]+$/.test(username + password)) {
      setError('Use ASCII credentials and a username without a colon.');
      return;
    }
    load(`Basic ${btoa(`${username}:${password}`)}`);
  }

  function signOut() {
    setAuthorization(null);
    setJobs([]);
    setNext(null);
    setError('');
  }

  return (
    <>
      <header className="top"><strong>AltaTherm</strong><span>Metrics</span></header>
      <main>
        <div className="heading">
          <h1>Oven jobs</h1>
          {authorization && <div className="actions">
            <button disabled={busy} onClick={() => load(authorization)}>Refresh</button>
            <button disabled={busy} onClick={signOut}>Sign out</button>
          </div>}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {authorization ? <>
          <JobTable jobs={jobs} />
          {next && <button className="older" disabled={busy} onClick={() => load(authorization, next)}>Load older jobs</button>}
        </> : (
          <form onSubmit={signIn}>
            <label>Username<input name="username" autoComplete="username" required /></label>
            <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
            <button disabled={busy} type="submit">{busy ? 'Signing in…' : 'Sign in'}</button>
          </form>
        )}
      </main>
    </>
  );
}

createRoot(document.getElementById('root')).render(<Dashboard />);
