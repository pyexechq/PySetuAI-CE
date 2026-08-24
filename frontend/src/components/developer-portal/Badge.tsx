import React from 'react';

export const Badge = ({ children, variant = 'default' }: { children: React.ReactNode, variant?: string }) => {
  const variants: Record<string, string> = {
    default: 'bg-gray-100 text-gray-800',
    primary: 'bg-blue-100 text-blue-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    danger: 'bg-red-100 text-red-800',
    dark: 'bg-gray-800 text-gray-100'
  };
  return <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${variants[variant] || variants.default}`}>{children}</span>;
};
