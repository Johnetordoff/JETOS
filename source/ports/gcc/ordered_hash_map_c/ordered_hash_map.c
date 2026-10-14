/*
 * Human-maintained C implementation of the JETOS ordered_hash_map port.
 * See ordered_hash_map.h for provenance and license.
 */
#include "ordered_hash_map.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static void *
grow_entries(void *entries, size_t *capacity, size_t entry_size)
{
    size_t next = *capacity ? *capacity * 2 : 8;
    void *memory = realloc(entries, next * entry_size);
    if (!memory)
        abort();
    *capacity = next;
    return memory;
}

static size_t
find_str_int_any(const jetos_omap_str_int *map, const char *key)
{
    for (size_t i = 0; i < map->length; ++i)
        if (map->entries[i].key == key)
            return i;
    return SIZE_MAX;
}

void
jetos_omap_str_int_init(jetos_omap_str_int *map)
{
    *map = (jetos_omap_str_int){0};
}

void
jetos_omap_str_int_destroy(jetos_omap_str_int *map)
{
    free(map->entries);
    *map = (jetos_omap_str_int){0};
}

bool
jetos_omap_str_int_copy(jetos_omap_str_int *dst, const jetos_omap_str_int *src)
{
    jetos_omap_str_int fresh = {0};
    if (src->length != 0) {
        fresh.entries = malloc(src->length * sizeof(*fresh.entries));
        if (!fresh.entries)
            return false;
        memcpy(fresh.entries, src->entries,
               src->length * sizeof(*fresh.entries));
        fresh.length = src->length;
        fresh.capacity = src->length;
        fresh.active_count = src->active_count;
    }
    jetos_omap_str_int_destroy(dst);
    *dst = fresh;
    return true;
}

bool
jetos_omap_str_int_put(jetos_omap_str_int *map, const char *key, int value)
{
    size_t index = find_str_int_any(map, key);
    if (index != SIZE_MAX) {
        bool existed = map->entries[index].active;
        map->entries[index].value = value;
        if (!existed) {
            map->entries[index].active = true;
            ++map->active_count;
        }
        return existed;
    }

    if (map->length == map->capacity)
        map->entries = grow_entries(
            map->entries, &map->capacity, sizeof(*map->entries)
        );

    map->entries[map->length++] = (jetos_omap_str_int_entry){
        .key = key,
        .value = value,
        .active = true,
    };
    ++map->active_count;
    return false;
}

int *
jetos_omap_str_int_get(jetos_omap_str_int *map, const char *key)
{
    size_t index = find_str_int_any(map, key);
    if (index == SIZE_MAX || !map->entries[index].active)
        return NULL;
    return &map->entries[index].value;
}

int *
jetos_omap_str_int_get_or_insert(jetos_omap_str_int *map, const char *key,
                               bool *existed)
{
    size_t index = find_str_int_any(map, key);
    if (index != SIZE_MAX && map->entries[index].active) {
        if (existed)
            *existed = true;
        return &map->entries[index].value;
    }

    if (existed)
        *existed = false;

    if (index != SIZE_MAX) {
        map->entries[index].active = true;
        map->entries[index].value = 0;
        ++map->active_count;
        return &map->entries[index].value;
    }

    if (map->length == map->capacity)
        map->entries = grow_entries(
            map->entries, &map->capacity, sizeof(*map->entries)
        );

    index = map->length++;
    map->entries[index] = (jetos_omap_str_int_entry){
        .key = key,
        .value = 0,
        .active = true,
    };
    ++map->active_count;
    return &map->entries[index].value;
}

void
jetos_omap_str_int_remove(jetos_omap_str_int *map, const char *key)
{
    size_t index = find_str_int_any(map, key);
    if (index != SIZE_MAX && map->entries[index].active) {
        map->entries[index].active = false;
        --map->active_count;
    }
}

size_t
jetos_omap_str_int_elements(const jetos_omap_str_int *map)
{
    return map->active_count;
}

bool
jetos_omap_str_int_nth_active(const jetos_omap_str_int *map, size_t n,
                            const char **key, int *value)
{
    size_t seen = 0;
    for (size_t i = 0; i < map->length; ++i) {
        if (!map->entries[i].active)
            continue;
        if (seen++ != n)
            continue;
        if (key)
            *key = map->entries[i].key;
        if (value)
            *value = map->entries[i].value;
        return true;
    }
    return false;
}

static size_t
find_int_str_any(const jetos_omap_int_str *map, int key)
{
    for (size_t i = 0; i < map->length; ++i)
        if (map->entries[i].key == key)
            return i;
    return SIZE_MAX;
}

void
jetos_omap_int_str_init(jetos_omap_int_str *map)
{
    *map = (jetos_omap_int_str){0};
}

void
jetos_omap_int_str_destroy(jetos_omap_int_str *map)
{
    free(map->entries);
    *map = (jetos_omap_int_str){0};
}

bool
jetos_omap_int_str_put(jetos_omap_int_str *map, int key, const char *value)
{
    size_t index = find_int_str_any(map, key);
    if (index != SIZE_MAX) {
        bool existed = map->entries[index].active;
        map->entries[index].value = value;
        if (!existed) {
            map->entries[index].active = true;
            ++map->active_count;
        }
        return existed;
    }

    if (map->length == map->capacity)
        map->entries = grow_entries(
            map->entries, &map->capacity, sizeof(*map->entries)
        );

    map->entries[map->length++] = (jetos_omap_int_str_entry){
        .key = key,
        .value = value,
        .active = true,
    };
    ++map->active_count;
    return false;
}

const char **
jetos_omap_int_str_get(jetos_omap_int_str *map, int key)
{
    size_t index = find_int_str_any(map, key);
    if (index == SIZE_MAX || !map->entries[index].active)
        return NULL;
    return &map->entries[index].value;
}

const char **
jetos_omap_int_str_get_or_insert(jetos_omap_int_str *map, int key, bool *existed)
{
    size_t index = find_int_str_any(map, key);
    if (index != SIZE_MAX && map->entries[index].active) {
        if (existed)
            *existed = true;
        return &map->entries[index].value;
    }

    if (existed)
        *existed = false;

    if (index != SIZE_MAX) {
        map->entries[index].active = true;
        map->entries[index].value = NULL;
        ++map->active_count;
        return &map->entries[index].value;
    }

    if (map->length == map->capacity)
        map->entries = grow_entries(
            map->entries, &map->capacity, sizeof(*map->entries)
        );

    index = map->length++;
    map->entries[index] = (jetos_omap_int_str_entry){
        .key = key,
        .value = NULL,
        .active = true,
    };
    ++map->active_count;
    return &map->entries[index].value;
}

size_t
jetos_omap_int_str_elements(const jetos_omap_int_str *map)
{
    return map->active_count;
}

bool
jetos_omap_int_str_nth_active(const jetos_omap_int_str *map, size_t n,
                            int *key, const char **value)
{
    size_t seen = 0;
    for (size_t i = 0; i < map->length; ++i) {
        if (!map->entries[i].active)
            continue;
        if (seen++ != n)
            continue;
        if (key)
            *key = map->entries[i].key;
        if (value)
            *value = map->entries[i].value;
        return true;
    }
    return false;
}
