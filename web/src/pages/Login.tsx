import { useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Calendar } from "lucide-react";
import LoginForm from "../components/auth/LoginForm";
import { useAuth } from "../context/AuthContext";

function Login() {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  // Redirect to intended path or dashboard if already authenticated
  if (isAuthenticated && !loading) {
    const from = location.state?.from?.pathname || "/dashboard";
    return <Navigate to={from} replace />;
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <Calendar className="h-12 w-12 text-primary" />
        </div>
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Meeting Room Reservation
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Sign in to your account to manage room reservations
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <LoginForm
            isLoggingIn={isLoggingIn}
            setIsLoggingIn={setIsLoggingIn}
          />

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">
                  Or continue with
                </span>
              </div>
            </div>

            <div className="mt-6">
              <button
                type="button"
                className="w-full inline-flex justify-center py-2 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-500 hover:bg-gray-50"
              >
                <span className="sr-only">Sign in with Google</span>
                <svg
                  className="h-5 w-5"
                  aria-hidden="true"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M12.545 10.239v3.821h5.445c-.712 2.315-2.647 3.972-5.445 3.972a6.033 6.033 0 110-12.064c1.498 0 2.866.549 3.921 1.453l2.814-2.814A9.969 9.969 0 0012.545 2C8.177 2 4.585 4.935 3.623 8.872A10.057 10.057 0 003 12c0 5.523 4.477 10 10 10a9.863 9.863 0 006.866-2.756c1.942-1.932 3.007-4.709 3.134-7.959 0-.334.006-.671-.031-1.001h-10.424v-.045z" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
