import axios from 'axios';
import api from './api';
import { Room, RoomUnavailability, ApiError } from '../types/models';

// Helper function to handle errors
const handleApiError = (error: unknown, defaultMessage: string): never => {
  if (axios.isAxiosError(error) && error.response?.data) {
    throw error.response.data;
  }
  throw { error: { message: defaultMessage } } as ApiError;
};

// Get all rooms with optional filtering
export const getRooms = async (filters = {}): Promise<Room[]> => {
  try {
    const response = await api.get('/rooms', { params: filters });
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to fetch rooms');
  }
};

// Get room by ID
export const getRoomById = async (id: number | string): Promise<Room> => {
  try {
    const response = await api.get(`/rooms/${id}`);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to fetch room');
  }
};

// Create a new room (admin only)
export const createRoom = async (roomData: Partial<Room>): Promise<Room> => {
  try {
    const response = await api.post('/rooms', roomData);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to create room');
  }
};

// Update room (admin only)
export const updateRoom = async (id: number | string, roomData: Partial<Room>): Promise<Room> => {
  try {
    const response = await api.put(`/rooms/${id}`, roomData);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to update room');
  }
};

// Delete room (admin only)
export const deleteRoom = async (id: number | string): Promise<{ message: string }> => {
  try {
    const response = await api.delete(`/rooms/${id}`);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to delete room');
  }
};

// Check room availability
export const checkRoomAvailability = async (params: {
  room_id: number | string;
  start_time: string;
  end_time: string;
  exclude_reservation_id?: number;
}): Promise<{ available: boolean }> => {
  try {
    const response = await api.get('/rooms/availability', { params });
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to check room availability');
  }
};

// Get room unavailability periods
export const getRoomUnavailability = async (roomId: number | string): Promise<RoomUnavailability[]> => {
  try {
    const response = await api.get(`/rooms/${roomId}/unavailability`);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to fetch room unavailability');
  }
};

// Add unavailability period (admin only)
export const addRoomUnavailability = async (
  roomId: number | string, 
  unavailabilityData: Omit<RoomUnavailability, 'id' | 'room_id'>
): Promise<RoomUnavailability> => {
  try {
    const response = await api.post(`/rooms/${roomId}/unavailability`, unavailabilityData);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to add room unavailability');
  }
};

// Delete unavailability period (admin only)
export const deleteRoomUnavailability = async (unavailabilityId: number | string): Promise<{ message: string }> => {
  try {
    const response = await api.delete(`/rooms/unavailability/${unavailabilityId}`);
    return response.data;
  } catch (error) {
    handleApiError(error, 'Failed to delete room unavailability');
  }
};