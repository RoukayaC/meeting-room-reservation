import api from './api';

// Get all rooms with optional filtering
export const getRooms = async (filters = {}) => {
  try {
    const response = await api.get('/rooms', { params: filters });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to fetch rooms' } };
  }
};

// Get room by ID
export const getRoomById = async (id) => {
  try {
    const response = await api.get(`/rooms/${id}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to fetch room' } };
  }
};

// Create a new room (admin only)
export const createRoom = async (roomData) => {
  try {
    const response = await api.post('/rooms', roomData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to create room' } };
  }
};

// Update room (admin only)
export const updateRoom = async (id, roomData) => {
  try {
    const response = await api.put(`/rooms/${id}`, roomData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to update room' } };
  }
};

// Delete room (admin only)
export const deleteRoom = async (id) => {
  try {
    const response = await api.delete(`/rooms/${id}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to delete room' } };
  }
};

// Check room availability
export const checkRoomAvailability = async (params) => {
  try {
    const response = await api.get('/rooms/availability', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to check room availability' } };
  }
};

// Get room unavailability periods
export const getRoomUnavailability = async (roomId) => {
  try {
    const response = await api.get(`/rooms/${roomId}/unavailability`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to fetch room unavailability' } };
  }
};

// Add unavailability period (admin only)
export const addRoomUnavailability = async (roomId, unavailabilityData) => {
  try {
    const response = await api.post(`/rooms/${roomId}/unavailability`, unavailabilityData);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to add room unavailability' } };
  }
};

// Delete unavailability period (admin only)
export const deleteRoomUnavailability = async (unavailabilityId) => {
  try {
    const response = await api.delete(`/rooms/unavailability/${unavailabilityId}`);
    return response.data;
  } catch (error) {
    throw error.response?.data || { error: { message: 'Failed to delete room unavailability' } };
  }
};