import api from './api';

// Login with email and password
export const login = async (email, password) => {
  try {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Login failed' } };
  }
};

// Validate JWT token
export const validateToken = async (token) => {
  try {
    const response = await api.get('/auth/validate', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Token validation failed' } };
  }
};

// Get available permissions
export const getPermissions = async () => {
  try {
    const response = await api.get('/auth/permissions');
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to fetch permissions' } };
  }
};

// Google OAuth login (redirect)
export const getGoogleAuthUrl = async (redirectUri) => {
  try {
    const response = await api.get('/auth/google/auth', {
      params: { redirect_uri: redirectUri }
    });
    return response.data.auth_url;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to get Google Auth URL' } };
  }
};

// Handle Google OAuth callback
export const handleGoogleCallback = async (code, redirectUri) => {
  try {
    const response = await api.post('/auth/google/callback', {
      code,
      redirect_uri: redirectUri
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Google authentication failed' } };
  }
};