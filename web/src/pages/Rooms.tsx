import RoomsList from '../components/rooms/RoomsList';

function Rooms() {
  return <RoomsList />;
}

export default Rooms;
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
