import { ReactNode } from 'react';
import './PageHeader.css';

interface PageHeaderProps {
  title: string;
  children?: ReactNode;
}

const PageHeader = ({ title, children }: PageHeaderProps) => {
  return (
    <div className="page-header-comp">
      <h1>{title}</h1>
      {children && <div className="page-header-actions">{children}</div>}
    </div>
  );
};

export default PageHeader;
