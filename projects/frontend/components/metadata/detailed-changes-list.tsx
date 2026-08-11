/*
 * Copyright (c) 2026 Amazon.com
 * This file is licensed under the MIT License.
 * See the LICENSE file in the project root for full license information.
 */
import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Pagination,
  Skeleton,
  Tooltip,
  IconButton,
  Collapse,
  Stack,
  Divider
} from '@mui/material';
import {
  FilterList as FilterIcon,
  Sort as SortIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Search as SearchIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import {
  DetailedChangesListProps,
  ChangeObject,
  ChangeType,
  ChangeSourceType,
  ChangeComponent,
  ChangeFilterOptions,
  ChangeSortOptions
} from '../../lib/types';
import { ChangeTypeIndicator } from './change-type-indicator';

/**
 * Detailed list component for displaying individual changes
 * Supports filtering, sorting, and pagination for large change sets
 */
export const DetailedChangesList: React.FC<DetailedChangesListProps> = ({
  changes,
  loading = false,
  initialDisplayCount = 10,
  enableFiltering = true,
  enableSorting = true,
  onChangeSelect
}) => {
  // State management
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(initialDisplayCount);
  const [showFilters, setShowFilters] = useState(false);
  const [expandedChanges, setExpandedChanges] = useState<Set<string>>(new Set());

  // Filter and sort state
  const [filters, setFilters] = useState<ChangeFilterOptions>({});
  const [sortOptions, setSortOptions] = useState<ChangeSortOptions>({
    sortBy: 'timestamp',
    sortDirection: 'desc'
  });

  // Loading state
  if (loading) {
    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Skeleton variant="text" width={200} height={32} />
          </Box>
          {[1, 2, 3].map((item) => (
            <Box key={item} sx={{ mb: 2 }}>
              <Skeleton variant="rectangular" height={80} />
            </Box>
          ))}
        </CardContent>
      </Card>
    );
  }

  // No changes state
  if (!changes || changes.length === 0) {
    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" color="text.secondary" align="center" sx={{ py: 4 }}>
            No changes to display
          </Typography>
        </CardContent>
      </Card>
    );
  }

  // Filter and sort changes
  const filteredAndSortedChanges = useMemo(() => {
    let filtered = [...changes];

    // Apply filters
    if (filters.changeTypes && filters.changeTypes.length > 0) {
      filtered = filtered.filter(change => filters.changeTypes!.includes(change.changeType));
    }
    if (filters.sourceTypes && filters.sourceTypes.length > 0) {
      filtered = filtered.filter(change => filters.sourceTypes!.includes(change.sourceType));
    }
    if (filters.components && filters.components.length > 0) {
      filtered = filtered.filter(change => filters.components!.includes(change.component));
    }
    if (filters.searchText && filters.searchText.trim()) {
      const searchLower = filters.searchText.toLowerCase();
      filtered = filtered.filter(change =>
        change.changeId.toLowerCase().includes(searchLower) ||
        (change.oldValue && String(change.oldValue).toLowerCase().includes(searchLower)) ||
        (change.newValue && String(change.newValue).toLowerCase().includes(searchLower)) ||
        (change.column && change.column.toLowerCase().includes(searchLower)) ||
        (change.row && String(change.row).includes(searchLower))
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortOptions.sortBy) {
        case 'timestamp':
          aValue = new Date(a.timestamp).getTime();
          bValue = new Date(b.timestamp).getTime();
          break;
        case 'changeType':
          aValue = a.changeType;
          bValue = b.changeType;
          break;
        case 'sourceType':
          aValue = a.sourceType;
          bValue = b.sourceType;
          break;
        case 'component':
          aValue = a.component;
          bValue = b.component;
          break;
        default:
          aValue = a.timestamp;
          bValue = b.timestamp;
      }

      if (aValue < bValue) return sortOptions.sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOptions.sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [changes, filters, sortOptions]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedChanges.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedChanges = filteredAndSortedChanges.slice(startIndex, startIndex + itemsPerPage);

  // Helper functions
  const toggleChangeExpansion = (changeId: string) => {
    const newExpanded = new Set(expandedChanges);
    if (newExpanded.has(changeId)) {
      newExpanded.delete(changeId);
    } else {
      newExpanded.add(changeId);
    }
    setExpandedChanges(newExpanded);
  };

  const clearFilters = () => {
    setFilters({});
    setCurrentPage(1);
  };

  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return '(empty)';
    if (typeof value === 'string' && value.trim() === '') return '(empty)';
    return String(value);
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Detailed Changes ({filteredAndSortedChanges.length})
          </Typography>

          <Box sx={{ display: 'flex', gap: 1 }}>
            {enableFiltering && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<FilterIcon />}
                onClick={() => setShowFilters(!showFilters)}
                sx={{ textTransform: 'none' }}
              >
                Filters
              </Button>
            )}
          </Box>
        </Box>

        {/* Filters Panel */}
        {enableFiltering && (
          <Collapse in={showFilters}>
            <Box sx={{
              p: 2,
              mb: 2,
              backgroundColor: 'grey.50',
              borderRadius: 1,
              border: '1px solid',
              borderColor: 'grey.200'
            }}>
              <Stack spacing={2}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Filter Changes
                  </Typography>
                  <Button
                    size="small"
                    startIcon={<ClearIcon />}
                    onClick={clearFilters}
                    sx={{ textTransform: 'none' }}
                  >
                    Clear All
                  </Button>
                </Box>

                <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
                  {/* Search */}
                  <TextField
                    size="small"
                    placeholder="Search changes..."
                    value={filters.searchText || ''}
                    onChange={(e) => setFilters({ ...filters, searchText: e.target.value })}
                    InputProps={{
                      startAdornment: <SearchIcon sx={{ mr: 1, color: 'text.secondary' }} />
                    }}
                  />

                  {/* Change Type Filter */}
                  <FormControl size="small">
                    <InputLabel>Change Type</InputLabel>
                    <Select
                      multiple
                      value={filters.changeTypes || []}
                      onChange={(e) => setFilters({
                        ...filters,
                        changeTypes: e.target.value as ChangeType[]
                      })}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selected.map((value) => (
                            <Chip key={value} label={value} size="small" />
                          ))}
                        </Box>
                      )}
                    >
                      {Object.values(ChangeType).map((type) => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  {/* Source Type Filter */}
                  <FormControl size="small">
                    <InputLabel>Source Type</InputLabel>
                    <Select
                      multiple
                      value={filters.sourceTypes || []}
                      onChange={(e) => setFilters({
                        ...filters,
                        sourceTypes: e.target.value as ChangeSourceType[]
                      })}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selected.map((value) => (
                            <Chip key={value} label={value} size="small" />
                          ))}
                        </Box>
                      )}
                    >
                      {Object.values(ChangeSourceType).map((type) => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  {/* Component Filter */}
                  <FormControl size="small">
                    <InputLabel>Component</InputLabel>
                    <Select
                      multiple
                      value={filters.components || []}
                      onChange={(e) => setFilters({
                        ...filters,
                        components: e.target.value as ChangeComponent[]
                      })}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {selected.map((value) => (
                            <Chip key={value} label={value} size="small" />
                          ))}
                        </Box>
                      )}
                    >
                      {Object.values(ChangeComponent).map((component) => (
                        <MenuItem key={component} value={component}>
                          {component}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>

                {/* Sort Options */}
                {enableSorting && (
                  <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                    <SortIcon sx={{ color: 'text.secondary' }} />
                    <FormControl size="small" sx={{ minWidth: 120 }}>
                      <InputLabel>Sort By</InputLabel>
                      <Select
                        value={sortOptions.sortBy}
                        onChange={(e) => setSortOptions({
                          ...sortOptions,
                          sortBy: e.target.value as any
                        })}
                      >
                        <MenuItem value="timestamp">Timestamp</MenuItem>
                        <MenuItem value="changeType">Change Type</MenuItem>
                        <MenuItem value="sourceType">Source Type</MenuItem>
                        <MenuItem value="component">Component</MenuItem>
                      </Select>
                    </FormControl>
                    <FormControl size="small" sx={{ minWidth: 100 }}>
                      <InputLabel>Order</InputLabel>
                      <Select
                        value={sortOptions.sortDirection}
                        onChange={(e) => setSortOptions({
                          ...sortOptions,
                          sortDirection: e.target.value as 'asc' | 'desc'
                        })}
                      >
                        <MenuItem value="desc">Newest</MenuItem>
                        <MenuItem value="asc">Oldest</MenuItem>
                      </Select>
                    </FormControl>
                  </Box>
                )}
              </Stack>
            </Box>
          </Collapse>
        )}

        {/* Changes List */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {paginatedChanges.map((change) => {
            const isExpanded = expandedChanges.has(change.changeId);

            return (
              <Card
                key={change.changeId}
                variant="outlined"
                sx={{
                  border: '1px solid',
                  borderColor: 'grey.300',
                  cursor: onChangeSelect ? 'pointer' : 'default',
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    borderColor: 'primary.main',
                    boxShadow: 1
                  }
                }}
                onClick={() => onChangeSelect?.(change)}
              >
                <CardContent sx={{ pb: 2 }}>
                  {/* Change Header */}
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <ChangeTypeIndicator
                        changeType={change.changeType}
                        sourceType={change.sourceType}
                        size="medium"
                        showLabel={true}
                      />

                      <Box>
                        <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                          {change.component} • {formatTimestamp(change.timestamp)}
                        </Typography>
                        {change.column && (
                          <Chip
                            label={change.row ? `Row ${change.row}, ${change.column}` : change.column}
                            size="small"
                            sx={{
                              mt: 0.5,
                              fontSize: '0.7rem',
                              height: 20,
                              backgroundColor: 'primary.main',
                              color: 'primary.contrastText'
                            }}
                          />
                        )}
                      </Box>
                    </Box>

                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleChangeExpansion(change.changeId);
                      }}
                    >
                      {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                    </IconButton>
                  </Box>

                  {/* Change Values */}
                  <Box sx={{
                    p: 2,
                    backgroundColor: 'grey.50',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'grey.200'
                  }}>
                    {change.changeType === ChangeType.RENAME && (
                      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            letterSpacing: 0.5
                          }}>
                            Previous Value
                          </Typography>
                          <Typography variant="body2" sx={{
                            mt: 0.5,
                            fontFamily: 'monospace',
                            fontSize: '0.875rem',
                            color: 'error.main'
                          }}>
                            {formatValue(change.oldValue)}
                          </Typography>
                        </Box>
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{
                            fontWeight: 600,
                            textTransform: 'uppercase',
                            letterSpacing: 0.5
                          }}>
                            New Value
                          </Typography>
                          <Typography variant="body2" sx={{
                            mt: 0.5,
                            fontFamily: 'monospace',
                            fontSize: '0.875rem',
                            color: 'success.main'
                          }}>
                            {formatValue(change.newValue)}
                          </Typography>
                        </Box>
                      </Box>
                    )}

                    {change.changeType === ChangeType.ADD && (
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          letterSpacing: 0.5
                        }}>
                          Added Value
                        </Typography>
                        <Typography variant="body2" sx={{
                          mt: 0.5,
                          fontFamily: 'monospace',
                          fontSize: '0.875rem',
                          color: 'success.main'
                        }}>
                          {formatValue(change.newValue)}
                        </Typography>
                      </Box>
                    )}

                    {change.changeType === ChangeType.REMOVE && (
                      <Box>
                        <Typography variant="caption" color="text.secondary" sx={{
                          fontWeight: 600,
                          textTransform: 'uppercase',
                          letterSpacing: 0.5
                        }}>
                          Removed Value
                        </Typography>
                        <Typography variant="body2" sx={{
                          mt: 0.5,
                          fontFamily: 'monospace',
                          fontSize: '0.875rem',
                          color: 'error.main'
                        }}>
                          {formatValue(change.oldValue)}
                        </Typography>
                      </Box>
                    )}
                  </Box>

                  {/* Expanded Details */}
                  <Collapse in={isExpanded}>
                    <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                      <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                        Additional Details
                      </Typography>

                      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 2 }}>
                        <Box>
                          <Typography variant="caption" color="text.secondary">Change ID</Typography>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                            {change.changeId}
                          </Typography>
                        </Box>

                        <Box>
                          <Typography variant="caption" color="text.secondary">Versions</Typography>
                          <Typography variant="body2">
                            {change.sourceVersion} → {change.targetVersion}
                          </Typography>
                        </Box>

                        {change.column && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">Location</Typography>
                            <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                              {change.row ? `Row ${change.row}, Column "${change.column}"` : `Column "${change.column}"`}
                            </Typography>
                          </Box>
                        )}

                        {change.confidenceScore !== undefined && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">Confidence</Typography>
                            <Typography variant="body2">
                              {Math.round(change.confidenceScore * 100)}%
                            </Typography>
                          </Box>
                        )}
                      </Box>
                    </Box>
                  </Collapse>
                </CardContent>
              </Card>
            );
          })}
        </Box>

        {/* Pagination */}
        {totalPages > 1 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={(_, page) => setCurrentPage(page)}
              color="primary"
              showFirstButton
              showLastButton
            />
          </Box>
        )}

        {/* No results message */}
        {filteredAndSortedChanges.length === 0 && changes.length > 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              No changes match the current filters
            </Typography>
            <Button
              variant="outlined"
              size="small"
              onClick={clearFilters}
              sx={{ mt: 1, textTransform: 'none' }}
            >
              Clear Filters
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};
