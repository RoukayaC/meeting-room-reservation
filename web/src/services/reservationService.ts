import axios from 'axios';
import api from './api';
import { Reservation, ReservationFormData, ApiError, ReservationFilters } from '../types/models';

// Helper function to handle errors
const handleApiError = (error: unknown, defaultMessage: string): never => {
  if (axios.isAxiosError(error) && error.response?.data) {
    throw error.response.data;
  }
  throw { error: { message: defaultMessage } } as ApiError;
};

// Get all reservations with optional filtering
export const getReservations = async (filters: ReservationFilters = {}): Promise<Reservation[]> => {
  try {
    const response = await api.get<Reservation[]>('/reservations', { params: filters });
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to fetch reservations');
  }
};

// Get reservation by ID
export const getReservationById = async (id: string | number): Promise<Reservation> => {
  try {
    const response = await api.get<Reservation>(`/reservations/${id}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to fetch reservation');
  }
};

// Create a new reservation
export const createReservation = async (reservationData: ReservationFormData): Promise<Reservation> => {
  try {
    const response = await api.post<Reservation>('/reservations', reservationData);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to create reservation');
  }
};

// Update reservation
export const updateReservation = async (id: string | number, reservationData: ReservationFormData): Promise<Reservation> => {
  try {
    const response = await api.put<Reservation>(`/reservations/${id}`, reservationData);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to update reservation');
  }
};

// Cancel reservation
export const cancelReservation = async (id: string | number): Promise<{ message: string }> => {
  try {
    const response = await api.delete<{ message: string }>(`/reservations/${id}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to cancel reservation');
  }
};

// Get reservations for a user
export const getUserReservations = async (userId: number): Promise<Reservation[]> => {
  try {
    const response = await api.get<Reservation[]>(`/reservations/user/${userId}`);
    return response.data;
  } catch (error) {
    return handleApiError(error, "Failed to fetch user's reservations");
  }
};

// Get reservations for a room
export const getRoomReservations = async (roomId: number, params = {}): Promise<Reservation[]> => {
  try {
    const response = await api.get<Reservation[]>(`/reservations/room/${roomId}`, { params });
    return response.data;
  } catch (error) {
    return handleApiError(error, "Failed to fetch room's reservations");
  }
};

// Check if a room is available at a specific time
export const checkReservationAvailability = async (params: {
  room_id: number;
  start_time: string;
  end_time: string;
  exclude_reservation_id?: number;
}): Promise<{ available: boolean }> => {
  try {
    const response = await api.get<{ available: boolean }>('/reservations/check', { params });
    return response.data;
  } catch (error) {
    return handleApiError(error, 'Failed to check reservation availability');
  }
};