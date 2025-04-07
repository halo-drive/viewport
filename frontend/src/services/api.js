//for prod
const API_BASE_URL = '';
//for dev
//const API_BASE_URL = 'http://localhost:443';

// Generic API request handler
async function apiRequest(url, method = 'GET', data = null) {
  const options = {
    method,
    headers: {},
    credentials: 'include' // Important for session cookies
  };

  // If sending form data
  if (data && data instanceof FormData) {
    options.body = data;
  } 
  // If sending JSON data
  else if (data) {
    options.headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${url}`, options);
    
    const responseData = await response.json();
    
    // For non-OK responses, format the error
    if (!response.ok) {
      throw {
        status: response.status,
        message: responseData.message || `API request failed with status ${response.status}`,
        data: responseData
      };
    }
    
    return responseData;
  } catch (error) {
    console.error('API request error:', error);
    throw error;
  }
}

// API functions for specific endpoints
export const api = {
  // Check if API is reachable
  checkStatus: () => apiRequest('/api/status'),
  
  // Auth functions
  checkAuthStatus: () => apiRequest('/api/auth/status'),
  login: (formData) => apiRequest('/api/auth/login', 'POST', formData),
  signup: (formData) => apiRequest('/api/auth/signup', 'POST', formData),
  logout: () => apiRequest('/api/auth/logout', 'POST'),
  
  // Admin functions
  getPendingUsers: () => apiRequest('/api/admin/pending-users'),
  approveUser: (formData) => apiRequest('/api/admin/approve-user', 'POST', formData),
  
  // Route calculation
  calculateDieselRoute: (formData) => apiRequest('/api/diesel/route', 'POST', formData),
  calculateHydrogenRoute: (formData) => apiRequest('/api/hydrogen/route', 'POST', formData),

  getAllUsers: () => apiRequest('/api/admin/get-all-users'),
  deleteUser: (formData) => apiRequest('/api/admin/delete-user', 'POST', formData)
};

export default api;