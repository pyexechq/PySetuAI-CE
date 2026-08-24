import React from 'react';

export const Button = ({ children, onClick, variant = 'primary', className = '', disabled = false, type = "button" }: { children: React.ReactNode, onClick?: (e: any) => void, variant?: string, className?: string, disabled?: boolean, type?: "button"|"submit"|"reset" }) => {
  const base = 'inline-flex items-center justify-center px-4 py-2 text-sm font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
  const variants: Record<string, string> = {
    primary: 'text-white bg-blue-600 hover:bg-blue-700',
    secondary: 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50',
    danger: 'text-white bg-red-600 hover:bg-red-700',
    ghost: 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
  };
  return <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${variants[variant] || variants.primary} ${className}`}>{children}</button>;
};
