import api from './api';

// Get all reservations with optional filtering
export const getReservations = async (filters = {}) => {
  try {
    const response = await api.get('/reservations', { params: filters });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to fetch reservations' } };
  }
};

// Get reservation by ID
export const getReservationById = async (id) => {
  try {
    const response = await api.get(`/reservations/${id}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to fetch reservation' } };
  }
};

// Create a new reservation
export const createReservation = async (reservationData) => {
  try {
    const response = await api.post('/reservations', reservationData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to create reservation' } };
  }
};

// Update reservation
export const updateReservation = async (id, reservationData) => {
  try {
    const response = await api.put(`/reservations/${id}`, reservationData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to update reservation' } };
  }
};

// Cancel reservation
export const cancelReservation = async (id) => {
  try {
    const response = await api.delete(`/reservations/${id}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to cancel reservation' } };
  }
};

// Get reservations for a user
export const getUserReservations = async (userId) => {
  try {
    const response = await api.get(`/reservations/user/${userId}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: "Failed to fetch user's reservations" } };
  }
};

// Get reservations for a room
export const getRoomReservations = async (roomId, params = {}) => {
  try {
    const response = await api.get(`/reservations/room/${roomId}`, { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: "Failed to fetch room's reservations" } };
  }
};

// Check if a room is available at a specific time
export const checkReservationAvailability = async (params) => {
  try {
    const response = await api.get('/reservations/check', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to check reservation availability' } };
  }
};