import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Plus, Search, Filter } from "lucide-react";
import { getRooms } from "../services/roomService";
import RoomCard from "../components/rooms/RoomCard";
import { useAuth } from "../context/AuthContext";

function Rooms() {
  const { isAdmin } = useAuth();
  const [filters, setFilters] = useState({
    capacity: "",
    type: "",
    has_projector: null,
    has_video_conf: null,
  });

  // Fetch rooms with filters
  const {
    data: rooms,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["rooms", filters],
    queryFn: () => getRooms(filters),
  });

  // Handle filter change
  const handleFilterChange = (e) => {
    const { name, value, type, checked } = e.target;

    if (type === "checkbox") {
      setFilters((prev) => ({
        ...prev,
        [name]: checked ? true : null, // true when checked, null when unchecked
      }));
    } else {
      setFilters((prev) => ({
        ...prev,
        [name]: value,
      }));
    }
  };

  // Clear all filters
  const clearFilters = () => {
    setFilters({
      capacity: "",
      type: "",
      has_projector: null,
      has_video_conf: null,
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 justify-between md:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Meeting Rooms</h1>
          <p className="text-muted-foreground">
            Available rooms for reservation
          </p>
        </div>

        {isAdmin() && (
          <Link
            to="/rooms/new"
            className="inline-flex items-center rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-foreground"
          >
            <Plus className="h-4 w-4 mr-2" />
            Add Room
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white p-4 shadow rounded-lg">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400"
                size={18}
              />
              <input
                type="text"
                placeholder="Search rooms..."
                className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>

          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center space-x-2">
              <Filter size={18} className="text-gray-400" />
              <span className="text-sm font-medium">Filters:</span>
            </div>

            <select
              name="type"
              value={filters.type}
              onChange={handleFilterChange}
              className="border border-gray-300 rounded-md p-2 text-sm"
            >
              <option value="">All Types</option>
              <option value="meeting">Meeting</option>
              <option value="conference">Conference</option>
              <option value="presentation">Presentation</option>
              <option value="workshop">Workshop</option>
            </select>

            <select
              name="capacity"
              value={filters.capacity}
              onChange={handleFilterChange}
              className="border border-gray-300 rounded-md p-2 text-sm"
            >
              <option value="">Any Capacity</option>
              <option value="5">5+ People</option>
              <option value="10">10+ People</option>
              <option value="20">20+ People</option>
              <option value="30">30+ People</option>
            </select>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="has_projector"
                name="has_projector"
                checked={filters.has_projector === true}
                onChange={handleFilterChange}
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
              />
              <label htmlFor="has_projector" className="text-sm">
                Projector
              </label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="has_video_conf"
                name="has_video_conf"
                checked={filters.has_video_conf === true}
                onChange={handleFilterChange}
                className="h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded"
              />
              <label htmlFor="has_video_conf" className="text-sm">
                Video Conferencing
              </label>
            </div>

            <button
              onClick={clearFilters}
              className="text-sm text-primary hover:text-primary-foreground"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Room Grid */}
      {isLoading ? (
        <div className="grid place-items-center h-64">
          <div className="w-16 h-16 border-4 border-primary border-solid rounded-full border-t-transparent animate-spin"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-400 text-red-700 px-4 py-3 rounded relative">
          <span className="block sm:inline">
            Failed to load rooms: {error.message}
          </span>
        </div>
      ) : rooms?.length === 0 ? (
        <div className="bg-white p-10 text-center rounded-lg shadow">
          <h3 className="text-lg font-medium mb-2">No rooms found</h3>
          <p className="text-muted-foreground">
            Try adjusting your filters or add a new room.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {rooms.map((room) => (
            <RoomCard key={room.id} room={room} />
          ))}
        </div>
      )}
    </div>
  );
}

export default Rooms;
