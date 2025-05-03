import axios from 'axios';
import api from './api';
import { User, ApiError } from '../types/models';

// Helper function to handle errors
const handleApiError = (error: unknown, defaultMessage: string): never => {
  if (axios.isAxiosError(error) && error.response?.data) {
    throw error.response.data;
  }
  throw { error: { message: defaultMessage } } as ApiError;
};

// Get all users (admin only)
export const getUsers = async (): Promise<User[]> => {
  try {
    const response = await api.get<User[]>('/users');
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to fetch users');
  }
};

// Get user by ID
export const getUserById = async (id: number | string): Promise<User> => {
  try {
    const response = await api.get<User>(`/users/${id}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to fetch user');
  }
};

// Create a new user (admin only)
export const createUser = async (userData: Partial<User>): Promise<User> => {
  try {
    const response = await api.post<User>('/users', userData);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to create user');
  }
};

// Update user
export const updateUser = async (id: number | string, userData: Partial<User>): Promise<User> => {
  try {
    const response = await api.put<User>(`/users/${id}`, userData);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to update user');
  }
};

// Delete user (admin only)
export const deleteUser = async (id: number | string): Promise<{ message: string }> => {
  try {
    const response = await api.delete<{ message: string }>(`/users/${id}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to delete user');
  }
};

// Get the current user's profile
export const getCurrentUser = async (): Promise<User> => {
  try {
    const response = await api.get<User>('/auth/validate');
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to get current user');
  }
};