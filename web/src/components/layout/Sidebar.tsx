import { Link, useLocation } from "react-router-dom";
import { Home, Users, Calendar, Grid3X3 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { cn } from "../../lib/utils";

function Sidebar() {
  const location = useLocation();
  const { isAdmin } = useAuth();

  const navItems = [
    {
      name: "Dashboard",
      icon: <Home size={20} />,
      path: "/dashboard",
      active: location.pathname === "/dashboard",
    },
    {
      name: "Rooms",
      icon: <Grid3X3 size={20} />,
      path: "/rooms",
      active: location.pathname.startsWith("/rooms"),
    },
    {
      name: "Reservations",
      icon: <Calendar size={20} />,
      path: "/reservations",
      active: location.pathname.startsWith("/reservations"),
    },
    // Only show Users for admins
    ...(isAdmin()
      ? [
          {
            name: "Users",
            icon: <Users size={20} />,
            path: "/users",
            active: location.pathname.startsWith("/users"),
          },
        ]
      : []),
  ];

  return (
    <aside className="sidebar hidden md:flex h-screen fixed z-10 md:sticky top-0 w-64 flex-shrink-0 bg-white border-r border-gray-200 flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center justify-center border-b border-gray-200">
        <Link to="/" className="flex items-center space-x-2">
          <Calendar className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold">MeetingRooms</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 pt-6 px-4 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.name}
            to={item.path}
            className={cn(
              "flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors",
              item.active
                ? "bg-primary text-primary-foreground"
                : "text-gray-600 hover:text-gray-900 hover:bg-gray-100"
            )}
          >
            <span className="mr-3">{item.icon}</span>
            <span>{item.name}</span>
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500">
          <p>Meeting Room System</p>
          <p>© 2025 All rights reserved</p>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
