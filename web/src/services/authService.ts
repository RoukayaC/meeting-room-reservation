import axios from 'axios';
import api from './api';
import { User, ApiError } from '../types/models';

interface LoginResponse {
  token: string;
  user: User;
}

// Helper function to handle errors
const handleApiError = (error: unknown, defaultMessage: string): never => {
  if (axios.isAxiosError(error) && error.response?.data) {
    throw error.response.data;
  }
  throw { error: { message: defaultMessage } } as ApiError;
};

// Login with email and password
export const login = async (email: string, password: string): Promise<LoginResponse> => {
  try {
    const response = await api.post<LoginResponse>('/auth/login', { email, password });
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Login failed');
  }
};

// Validate JWT token
export const validateToken = async (token: string): Promise<User> => {
  try {
    const response = await api.get<User>('/auth/validate', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Token validation failed');
  }
};

// Get available permissions
export const getPermissions = async (): Promise<string[]> => {
  try {
    const response = await api.get<string[]>('/auth/permissions');
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to fetch permissions');
  }
};

// Google OAuth login (redirect)
export const getGoogleAuthUrl = async (redirectUri: string): Promise<string> => {
  try {
    const response = await api.get<{ auth_url: string }>('/auth/google/auth', {
      params: { redirect_uri: redirectUri }
    });
    return response.data.auth_url;
  } catch (error) {
    return handleApiError(error, 'Failed to get Google Auth URL');
  }
};

// Handle Google OAuth callback
export const handleGoogleCallback = async (code: string, redirectUri: string): Promise<LoginResponse> => {
  try {
    const response = await api.post<LoginResponse>('/auth/google/callback', {
      code,
      redirect_uri: redirectUri
    });
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Google authentication failed');
  }
};