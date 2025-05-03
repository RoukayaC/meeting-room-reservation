import React from 'react';

interface LoadingProps {
  size?: 'small' | 'medium' | 'large';
  className?: string;
}

const Loading: React.FC<LoadingProps> = ({ 
  size = 'medium', 
  className = ''
}) => {
  // Determine spinner size
  const sizeClasses = {
    small: 'w-6 h-6 border-2',
    medium: 'w-12 h-12 border-3',
    large: 'w-16 h-16 border-4',
  };
  
  const sizeClass = sizeClasses[size];
  
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div 
        className={`${sizeClass} border-primary border-solid rounded-full border-t-transparent animate-spin`}
      />
    </div>
  );
};

export default Loading;
