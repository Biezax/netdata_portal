// Wraps fetch so any 401 from the backend gate bounces the user to the login page.
export async function fetchJson(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const response = await fetch(input, init);
  if (response.status === 401 && typeof window !== 'undefined') {
    window.location.assign('/login');
  }
  return response;
}
