import React from 'react';
import { FaPenFancy, FaFolderOpen, FaMicrochip } from 'react-icons/fa';
import './PlaceholderContent.css';

const PlaceholderContent = ({ section }) => {
  const configs = {
    document: {
      icon: FaFolderOpen,
      title: 'Smart Docs',
      description: 'Drawings · specs · revision control'
    },
    iot: {
      icon: FaMicrochip,
      title: 'Smart IoT',
      description: 'Structural health · environmental'
    }
  };

  const config = configs[section] || configs.form;
  const Icon = config.icon;

  return (
    <div className="placeholder-content">
      <Icon />
      <h3>{config.title}</h3>
      <p>{config.description}</p>
    </div>
  );
};

export default PlaceholderContent;