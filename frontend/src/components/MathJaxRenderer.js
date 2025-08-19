import React, { useEffect, useRef } from 'react';

const MathJaxRenderer = ({ children, className = "" }) => {
  const mathJaxRef = useRef(null);

  useEffect(() => {
    if (window.MathJax) {
      // Process the MathJax content
      window.MathJax.typesetPromise([mathJaxRef.current]).catch((err) => {
        console.error('MathJax rendering error:', err);
      });
    }
  }, [children]);

  return (
    <div ref={mathJaxRef} className={`math-content ${className}`}>
      {children}
    </div>
  );
};

export default MathJaxRenderer;