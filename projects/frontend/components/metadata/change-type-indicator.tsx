/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React from 'react';
import {
  Chip,
  Tooltip,
  Box,
  Typography
} from '@mui/material';
import {
  Add as AddIcon,
  Remove as RemoveIcon,
  Edit as EditIcon,
  Computer as SystemIcon,
  Person as UserIcon
} from '@mui/icons-material';
import { ChangeType, ChangeSourceType, ChangeTypeIndicatorProps } from '../../lib/types';

/**
 * Visual indicator component for change types with source attribution
 * Displays change type (add/remove/rename) and source (system/user) with appropriate styling
 */
export const ChangeTypeIndicator: React.FC<ChangeTypeIndicatorProps> = ({
  changeType,
  sourceType,
  size = 'medium',
  showLabel = true,
  tooltipText
}) => {
  // Get change type configuration
  const getChangeTypeConfig = () => {
    switch (changeType) {
      case ChangeType.ADD:
        return {
          icon: <AddIcon fontSize={size === 'small' ? 'small' : 'medium'} />,
          label: 'Added',
          color: '#4caf50', // Green
          backgroundColor: '#e8f5e8'
        };
      case ChangeType.REMOVE:
        return {
          icon: <RemoveIcon fontSize={size === 'small' ? 'small' : 'medium'} />,
          label: 'Removed',
          color: '#f44336', // Red
          backgroundColor: '#ffeaea'
        };
      case ChangeType.RENAME:
        return {
          icon: <EditIcon fontSize={size === 'small' ? 'small' : 'medium'} />,
          label: 'Modified',
          color: '#ff9800', // Orange
          backgroundColor: '#fff3e0'
        };
      default:
        return {
          icon: <EditIcon fontSize={size === 'small' ? 'small' : 'medium'} />,
          label: 'Changed',
          color: '#757575', // Gray
          backgroundColor: '#f5f5f5'
        };
    }
  };

  // Get source type configuration
  const getSourceTypeConfig = () => {
    switch (sourceType) {
      case ChangeSourceType.SYSTEM:
        return {
          icon: <SystemIcon fontSize="small" />,
          label: 'System',
          color: '#2196f3', // Blue
          backgroundColor: '#e3f2fd'
        };
      case ChangeSourceType.USER:
        return {
          icon: <UserIcon fontSize="small" />,
          label: 'User',
          color: '#9c27b0', // Purple
          backgroundColor: '#f3e5f5'
        };
      default:
        return {
          icon: <SystemIcon fontSize="small" />,
          label: 'Unknown',
          color: '#757575', // Gray
          backgroundColor: '#f5f5f5'
        };
    }
  };

  const changeConfig = getChangeTypeConfig();
  const sourceConfig = getSourceTypeConfig();

  // Generate tooltip text
  const defaultTooltipText = `${changeConfig.label} by ${sourceConfig.label.toLowerCase()}`;
  const finalTooltipText = tooltipText || defaultTooltipText;

  // Size configurations
  const sizeConfig = {
    small: {
      chipHeight: 20,
      fontSize: '0.7rem',
      iconSize: 14,
      spacing: 0.5
    },
    medium: {
      chipHeight: 24,
      fontSize: '0.75rem',
      iconSize: 16,
      spacing: 1
    },
    large: {
      chipHeight: 28,
      fontSize: '0.875rem',
      iconSize: 18,
      spacing: 1
    }
  };

  const currentSizeConfig = sizeConfig[size];

  return (
    <Tooltip title={finalTooltipText} arrow>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: currentSizeConfig.spacing }}>
        {/* Change Type Indicator */}
        <Chip
          icon={changeConfig.icon}
          label={showLabel ? changeConfig.label : undefined}
          size={size === 'large' ? 'medium' : 'small'}
          sx={{
            height: currentSizeConfig.chipHeight,
            fontSize: currentSizeConfig.fontSize,
            fontWeight: 'bold',
            backgroundColor: changeConfig.backgroundColor,
            color: changeConfig.color,
            border: `1px solid ${changeConfig.color}`,
            '& .MuiChip-icon': {
              color: changeConfig.color,
              fontSize: currentSizeConfig.iconSize
            },
            '& .MuiChip-label': {
              paddingLeft: showLabel ? 1 : 0,
              paddingRight: showLabel ? 1 : 0
            }
          }}
        />

        {/* Source Type Indicator */}
        <Chip
          icon={sourceConfig.icon}
          label={showLabel ? sourceConfig.label : undefined}
          size={size === 'large' ? 'medium' : 'small'}
          variant="outlined"
          sx={{
            height: currentSizeConfig.chipHeight,
            fontSize: currentSizeConfig.fontSize,
            fontWeight: 'bold',
            backgroundColor: sourceConfig.backgroundColor,
            color: sourceConfig.color,
            borderColor: sourceConfig.color,
            '& .MuiChip-icon': {
              color: sourceConfig.color,
              fontSize: currentSizeConfig.iconSize
            },
            '& .MuiChip-label': {
              paddingLeft: showLabel ? 1 : 0,
              paddingRight: showLabel ? 1 : 0
            }
          }}
        />
      </Box>
    </Tooltip>
  );
};

/**
 * Simplified change type indicator that only shows the change type
 */
export const SimpleChangeTypeIndicator: React.FC<{
  changeType: ChangeType;
  size?: 'small' | 'medium' | 'large';
}> = ({ changeType, size = 'medium' }) => {
  const config = {
    [ChangeType.ADD]: {
      icon: <AddIcon />,
      color: '#4caf50',
      backgroundColor: '#e8f5e8',
      label: 'Added'
    },
    [ChangeType.REMOVE]: {
      icon: <RemoveIcon />,
      color: '#f44336',
      backgroundColor: '#ffeaea',
      label: 'Removed'
    },
    [ChangeType.RENAME]: {
      icon: <EditIcon />,
      color: '#ff9800',
      backgroundColor: '#fff3e0',
      label: 'Modified'
    }
  };

  const changeConfig = config[changeType];

  return (
    <Tooltip title={changeConfig.label} arrow>
      <Chip
        icon={changeConfig.icon}
        size={size === 'large' ? 'medium' : 'small'}
        sx={{
          height: size === 'small' ? 20 : size === 'large' ? 28 : 24,
          backgroundColor: changeConfig.backgroundColor,
          color: changeConfig.color,
          border: `1px solid ${changeConfig.color}`,
          '& .MuiChip-icon': {
            color: changeConfig.color
          }
        }}
      />
    </Tooltip>
  );
};
